import os
import re
from glob import glob

from antlr4 import CommonTokenStream, ParserRuleContext
from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.Errors import CancellationException
from antlr4.TokenStreamRewriter import TokenStreamRewriter

from . import io
from .parser.CMakeParser import CMakeParser
from .parser.CMakeParserListener import CMakeParserListener as CMakeListener


def list_if_none(arg: list | None) -> list:
    if arg is None:
        return []
    else:
        return arg


class TargetNode:
    def __init__(
        self,
        name: str,
        headers: list[str] = None,
        sources: list[str] = None,
        is_interface: bool = False,
        alias_for=None,
        cml_path=None,
    ) -> None:
        if not name:
            raise Exception("Can not create target without name!")
        self.name: str = name
        self.headers: list[str] = list_if_none(headers)
        self.cpp_includes: list[str] = []
        self.h_includes: list[str] = []
        self.sources: list[str] = list_if_none(sources)
        # targets parsed from source files
        self.public_targets: list[TargetNode] = []
        self.private_targets: list[TargetNode] = []
        # targets parsed from cml
        self.ppublic_targets: list[TargetNode] = []
        self.pprivate_targets: list[TargetNode] = []
        # interface targets can not be detected via code
        self.interface_targets: list[TargetNode] = []
        self.is_interface = is_interface
        self.alias_for: TargetNode | None = alias_for
        self.cml_path: str | None = cml_path
        self.is_object_lib = False
        self.was_linked = False

    def __str__(self) -> str:
        message: str = self.name + ":\n"
        if self.alias_for:
            message += f"Alias for {self.alias_for.name}\n"
            return message + self.alias_for.__str__()

        if self.is_interface:
            message += "Interface Target\n"

        message += "Dir:\n"
        message += "" if self.cml_path is None else self.cml_path
        message += "\nSources:\n"
        message += "\n".join(sorted(self.sources))
        message += "\nHeaders:\n"
        message += "\n".join(sorted(self.headers))
        message += "\nPrivate includes:\n"
        message += "\n".join(self.cpp_includes)
        message += "\nPublic includes:\n"
        message += "\n".join(self.h_includes)
        message += "\nPublic Targets:\n"
        message += "\n".join([t.name for t in self.public_targets])
        message += "\nPrivate Targets:\n"
        message += "\n".join([t.name for t in self.private_targets])
        message += "\nPublic Targets(cml):\n"
        message += "\n".join([t.name for t in self.ppublic_targets])
        message += "\nPrivate Targets(cml):\n"
        message += "\n".join([t.name for t in self.pprivate_targets])
        message += "\nInterface Targets(cml):\n"
        message += "\n".join([t.name for t in self.interface_targets])
        return message


class SyntaxErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        super().syntaxError(recognizer, offendingSymbol, line, column, msg, e)
        file_name = recognizer.getInputStream().tokenSource._input.fileName
        raise CancellationException(f"{file_name} line {line}:{column} {msg}")


class BaseListener(CMakeListener):
    def __init__(self, targets: dict[str, TargetNode]) -> None:
        super().__init__()
        self.targets = targets

    def ensure_target(self, target: str) -> TargetNode:
        node: None | TargetNode = self.targets.get(target)
        if node is None:
            node = TargetNode(target)
            self.targets[target] = node

        return node

    def get_args(self, ctx: ParserRuleContext):
        """
        Arguments in CMake can be quoted using '"' but this makes no difference
        for the parsing in this package so we strip the quotes.
        """
        args = [arg.getText() for arg in ctx.arguments().single_argument()]
        return [arg.replace('"', "") for arg in args]


class TargetInputListener(BaseListener):
    def __init__(self, targets, header_target_map=None, repo_root="") -> None:
        super().__init__(targets)
        self.in_if = False
        self.header_target_map = header_target_map
        self.repo_root = repo_root

    def exitAdd_target(self, ctx: CMakeParser.Add_targetContext):
        """
        This function is triggered by a cmake command that adds a target.
        For any one target this function can only be called once in a valid
        cmake project.

        As this function is not handling conditionals yet a repeat call of this
        function will only raise a warning not an error.

        This function assumes valid cmake input.
        Header files end on .h or .hpp.
        Files that end on .c* are source files (this ignores non c/++ files
        as we don't want to analyse them).
        """
        cmd = ctx.command.text.lower()
        args = self.get_args(ctx)

        if len(args) == 0:
            raise Exception(f"`{cmd}` called without arguments!")

        if len(ctx.arguments().compound_argument()) > 0:
            raise Exception(f"Compound arguments not valid for `{cmd}`!")

        cml_path = os.path.dirname(ctx.start.getInputStream().fileName)
        name = args[0]
        target = self.ensure_target(name)
        args = self.clean_target_args(args)

        if len(args) == 1:
            return

        if len(args) == 3 and args[1] == "ALIAS":
            target.alias_for = self.ensure_target(args[2])
            # alias targets have no other properties
            return

        if args[1] == "OBJECT":
            target.is_object_lib = True
            del args[1]
        elif args[1] == "INTERFACE":
            target.is_interface = True
            del args[1]

        self.add_target_sources(args, cml_path)

        if target.cml_path is not None:
            Warning(f"Repeated creation of target {name}!")

        target.cml_path = cml_path

    def exitModify_target(self, ctx: CMakeParser.Modify_targetContext):
        cmd = ctx.command.text.lower()

        args = self.get_args(ctx)

        if cmd == "target_link_libraries":
            self.add_linked_targets(args)

        if cmd == "target_sources":
            args = self.clean_target_args(args)
            cml_path = os.path.dirname(ctx.start.getInputStream().fileName)
            self.add_target_sources(args, cml_path)

    def add_linked_targets(self, args: list[str]):
        name = args[0]
        target = self.ensure_target(name)
        # Skip any target_link_library calls after the primary one
        # as we currently have no way to model these properly
        if target.was_linked:
            return

        linked_targets = self.handle_link_args(args[1:])
        target.ppublic_targets.extend(linked_targets["public"])
        target.pprivate_targets.extend(linked_targets["private"])
        target.interface_targets.extend(linked_targets["interface"])
        target.was_linked = True

    def add_target_sources(self, args: list[str], cml_path: str):
        target = self.ensure_target(args[0])
        files = args[1:]
        # expand paths to absolute, default is relative to current cml location
        files = [f.replace("${CMAKE_CURRENT_LIST_DIR}/", cml_path) for f in files]
        files = [os.path.join(cml_path, f) for f in files if not os.path.dirname(f)]
        sources, headers = self.sort_files(files)
        headers.extend(
            [h for h in glob(cml_path + "/*.h*") if io.has_matching_src(h, sources)]
        )
        target.headers.extend(headers)
        target.sources.extend(sources)

        if self.header_target_map is not None:
            for h in headers:
                if h not in self.header_target_map:
                    self.header_target_map[h.removeprefix(self.repo_root)] = []

                self.header_target_map[h.removeprefix(self.repo_root)].append(target)

    def sort_files(self, files: list[str]) -> tuple[list[str], list[str]]:
        """
        This function purposely ignore potential scope keywords for source files as
        we don't model them at this time.
        """
        sources = [
            f
            for f in files
            if os.path.splitext(f)[1] in [".c", ".cpp", ".cxx", ".cc", ".c++"]
        ]
        # This is only explicitly added headers!
        headers = [f for f in files if os.path.splitext(f)[1] in [".h", ".hpp"]]
        return sources, headers

    def clean_target_args(self, args: list[str]) -> list[str]:
        unused_keywords = [
            "EXCLUDE_FROM_ALL",
            "WIN32",
            "MACOSX",
            "IMPORTED",
            "GLOBAL",
            "STATIC",
            "SHARED",
            "MODULE",
        ]
        args = [arg for arg in args if arg not in unused_keywords]
        # remove variables and generator expressions as we can not deal with them
        genexpr_or_vars = r"^\$<.*>$|^\$\{.*\}$"

        args = [arg for arg in args if not re.match(genexpr_or_vars, arg)]
        return args

    def handle_link_args(self, args: list[str]) -> dict[str, list[TargetNode]]:
        """
        This function only handles a subset of the possible args to
        target_link_libraries:
        <PRIVATE|PUBLIC|INTERFACE> <item>...
        [<PRIVATE|PUBLIC|INTERFACE> <item>...]*
        with the target name already removed.

        Variables as targets are allowed. Generator expressions and name
        completed via variables ('some_${other_options}') are removed as
        the same string can represent multiple targets.
        """
        genexpr_or_partial = r"^\$<.*>$|.+\$\{.*\}$|^\$\{.*\}.+"
        clean_args = [arg for arg in args if not re.match(genexpr_or_partial, arg)]
        if len(args) > len(clean_args):
            Warning(
                f"Removed the following invalid targets: {set(args).difference(clean_args)}"
            )

        targets: dict[str, list[TargetNode]] = {
            "public": [],
            "private": [],
            "interface": [],
        }

        scope = "public"

        for item in clean_args:
            if item in {"PUBLIC", "INTERFACE", "PRIVATE"}:
                scope = item.lower()
            else:
                targets[scope].append(self.ensure_target(item))

        return targets


class UpdateTargetsListener(BaseListener):
    def __init__(self, targets: dict[str, TargetNode], token_stream: CommonTokenStream):
        super().__init__(targets)
        self.token_stream = TokenStreamRewriter(token_stream)

    def exitModify_target(self, ctx: CMakeParser.Modify_targetContext):
        args = self.get_args(ctx)
        target = self.ensure_target(args[0])

        if not target.cml_path:
            return

        def sort_targets(targets: list[str]):
            # We want to list the internal targets first
            a = [t for t in targets if t.startswith("velox")]
            b = [t for t in targets if not t.startswith("velox")]

            return sorted(a) + sorted(b)

        if not target.was_linked:
            public_targets = target.public_targets
            public_targets.extend(
                [
                    t
                    for t in target.ppublic_targets
                    if target.is_interface
                    or t.is_object_lib
                    or t.is_interface
                    or t.name.startswith("${")
                ]
            )
            private_targets = [
                t for t in target.private_targets if t not in public_targets
            ]
            private_targets.extend(
                [
                    t
                    for t in target.pprivate_targets
                    if t.is_object_lib or t.is_interface or t.name.startswith("${")
                ]
            )
            public_targets = sort_targets([*set([t.name for t in public_targets])])
            private_targets = sort_targets([*set([t.name for t in private_targets])])
            start = ctx.start.tokenIndex + 2
            stop = ctx.stop.tokenIndex - 1

            if (
                len(public_targets) + len(private_targets) == 0
                and not target.is_interface
            ):
                public_targets = [
                    t.name for t in target.ppublic_targets + target.pprivate_targets
                ]
                if len(public_targets) == 0:
                    print(target)
                    raise Exception(f"No targets to link to found for `{target.name}`")

            # don't linke to itself
            if target.name in public_targets:
                public_targets.remove(target.name)

            if target.name in private_targets:
                private_targets.remove(target.name)

            p_text = f' PUBLIC {" ".join(public_targets)}' if public_targets else ""
            pr_text = f' PRIVATE {" ".join(private_targets)}' if private_targets else ""
            new = f"{target.name}" + p_text + pr_text
            if target.is_interface:
                new = f'{target.name} INTERFACE {" ".join(sort_targets(public_targets + private_targets))}'
            self.token_stream.replaceRange(start, stop, new)
            target.was_linked = True
        else:
            scopes = ["INTERFACE", "PUBLIC", "PRIVATE"]
            if not any(scope in args for scope in scopes):
                # if a target was linked with a keyword all other
                # occurences of target_link_libraries must also use
                # a keyword
                self.token_stream.insertAfter(
                    ctx.start.tokenIndex + 3,
                    f'{"INTERFACE" if target.is_interface else "PUBLIC"} ',
                )
