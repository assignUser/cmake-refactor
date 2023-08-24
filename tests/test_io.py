import os
import tempfile

from cmake_refactor import io, listeners

current_dir = os.path.dirname(os.path.abspath(__file__))
cml = os.path.join(current_dir, "files/CMakeLists.txt")
velox_dir = os.path.join(current_dir, "velox/velox")


def test_file_roundtrip():
    original = cml
    stream = io.get_token_stream(original)

    with tempfile.NamedTemporaryFile() as new:
        io.write_token_stream(new.name, stream)
        new_contents = new.read().decode("utf-8")

    with open(original, "r", encoding="utf-8") as orig:
        original_contents = orig.read()

    assert original_contents.splitlines() == new_contents.splitlines()


class Listener_test(listeners.BaseListener):
    def __init__(self) -> None:
        super().__init__({})
        self.counter = 0

    def exitAdd_target(self, ctx: io.CMakeParser.Add_targetContext):
        self.counter += 1
        print("Found target:", ctx.arguments().single_argument()[0].getText())


def test_listener():
    stream = io.get_token_stream(cml)
    listener = Listener_test()
    io.walk_stream(stream, listener)
    assert listener.counter == 6


def test_find_file():
    file = "CMakeLists.txt"
    files = io.find_files(file, current_dir + "/files")
    assert len(files) == 1


def test_parse_dir():
    file = "CMakeLists.txt"
    repo = velox_dir
    files = io.find_files(file, repo, ["type_calculation", "experimental"])
    targets = {}

    for f in files:
        io.parse_targets(f, targets)
    print(len(targets))
    print(targets["velox_common_base"])
    print(targets["velox_flag_definitions"])
    assert targets["velox_flag_definitions"].is_object_lib


def test_get_includes():
    file = os.path.join(current_dir, "files/BitUtil.cpp")
    incs = io.get_includes(file)
    assert len(incs[0]) == 3
    assert len(incs[1]) == 2


def test_get_dep():
    assert io.get_dep_name("snappy.h") == "Snappy::snappy"
    assert io.get_dep_name("thrift/protovol/TCompactProtocol.h") == "thrift::thrift"
    assert io.get_dep_name("folly/synchronization/AtomicStruct.h") == "Folly::folly"
    assert io.get_dep_name("glog/glog.h") == "glog::glog"


def test_header_map():
    # TODO deal with the trailing / in the function
    repo_root = os.path.dirname(velox_dir) + os.path.sep
    file = "CMakeLists.txt"
    repo = velox_dir
    files = io.find_files(file, repo, ["experimental"])
    targets = {}
    hm = {}
    for f in files:
        # print("Parsing: ", f)
        io.parse_targets(f, targets, header_target_map=hm, repo_root=repo_root)
    io.map_local_headers(targets, hm, repo_root)
    print(hm.keys())
    assert targets.get("velox_common_base") is not None
    assert hm.get("velox/common/base/VeloxException.h") is not None


def test_full_update():
    io.update_links("velox/", os.path.dirname(velox_dir), ["proto","external"])


def test_full_update_reprex():
    io.update_links("velox", os.path.join(current_dir, "reprex/"))


def test_reprex():
    repo_root = os.path.join(current_dir, "reprex/")
    file = "CMakeLists.txt"
    files = io.find_files(file, repo_root + "velox/", ['proto'])
    targets = {}
    hm = {}
    for f in files:
        io.parse_targets(f, targets, header_target_map=hm, repo_root=repo_root)

    io.map_local_headers(targets, hm, repo_root)

    print(targets.values())
    for t in hm.values():
        print(t)

    assert targets["io"].private_targets[0] == targets["util"]
    assert targets["io"].private_targets[0] == targets["io"].ppublic_targets[0]
    assert targets["util"].public_targets[0] == targets["io"]
    assert targets["util"].public_targets[0] == targets["util"].ppublic_targets[0]

    for t in targets.values():
        t.was_linked = False

    token_stream = io.get_token_stream(
        os.path.join(repo_root, "velox/io/CMakeLists.txt")
    )
    update_listener = listeners.UpdateTargetsListener(targets, token_stream)
    io.walk_stream(token_stream, update_listener)

    updated_cml = update_listener.token_stream.getText("default", 0, 999999999)
    print(updated_cml)
    assert "PRIVATE util" in updated_cml
