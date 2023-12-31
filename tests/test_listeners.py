import os

from cmake_refactor import io, listeners

current_dir = os.path.dirname(os.path.abspath(__file__))
cml = os.path.join(current_dir, "files/CMakeLists.txt")


def test_listener_util():
    listener = listeners.TargetInputListener({})
    # making sure the regex are correct
    dirty_args = [
        "${var}",
        "${CMAKE_CURRENT_LIST_DIR}/file.h",
        "$<if:$<nested genexpr>>",
    ]
    assert listener.clean_target_args(dirty_args) == [
        "${CMAKE_CURRENT_LIST_DIR}/file.h",
    ]


def test_source_listener():
    stream = io.get_token_stream(cml)
    targets: dict[str, listeners.TargetNode] = {}
    listener = listeners.TargetInputListener(targets)
    io.walk_stream(stream, listener)
    assert len(targets["velox_common_base"].sources) == 9


def test_link_listener():
    stream = io.get_token_stream(cml)
    targets: dict[str, listeners.TargetNode] = {}
    listener = listeners.TargetInputListener(targets)
    io.walk_stream(stream, listener)
    velox_exception_public = [
        "velox_flag_definitions",
        "velox_process",
        "glog::glog",
        "Folly::folly",
        "fmt::fmt",
        "gflags::gflags",
    ]
    velox_common_base_public = ["velox_exception"]
    velox_common_base_private = ["velox_process", "xsimd"]

    assert velox_exception_public == [
        f.name for f in targets["velox_exception"].ppublic_targets
    ]
    assert velox_common_base_public == [
        f.name for f in targets["velox_common_base"].ppublic_targets
    ]
    assert velox_common_base_private == [
        f.name for f in targets["velox_common_base"].pprivate_targets
    ]


def test_alias_listener():
    stream = io.get_token_stream(cml)
    targets: dict[str, listeners.TargetNode] = {}
    listener = listeners.TargetInputListener(targets)
    io.walk_stream(stream, listener)
    assert targets["velox::exception"].alias_for.name == "velox_exception"


def test_interface_listener():
    stream = io.get_token_stream(cml)
    targets: dict[str, listeners.TargetNode] = {}
    listener = listeners.TargetInputListener(targets)
    io.walk_stream(stream, listener)


def test_link_replacement():
    repo_root = os.path.join(current_dir, "velox") + '/' 
    file = "CMakeLists.txt"
    repo = os.path.join(repo_root, "velox")
    files = io.find_files(file, repo, ["proto"])
    targets: dict[str, listeners.TargetNode] = {}
    hm = {}
    for f in files:
        # print(f"parsing {f}")
        io.parse_targets(f, targets, header_target_map=hm, repo_root=repo_root)
    io.map_local_headers(targets, hm, repo_root)

    for t in targets.values():
        t.was_linked = False
    token_stream = io.get_token_stream(
        os.path.join(current_dir, "files/caching_cml.txt")
    )
    update_listener = listeners.UpdateTargetsListener(targets, token_stream)
    io.walk_stream(token_stream, update_listener)

    updated_cml = update_listener.token_stream.getText("default", 0, 999999999)
    print(updated_cml)
    assert "PUBLIC" in updated_cml
