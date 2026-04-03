from agentauth.core.registry import Registry


def test_registry_register_and_get():
    reg: Registry = Registry("test")

    @reg.register("key1")
    class Test1:
        pass

    assert reg.get("key1") == Test1
    assert reg.get("missing") is None


def test_registry_discover_mock():
    reg: Registry = Registry("test")
    # Method catches ImportError and logs it, returns None
    reg.discover("non.existent.path")


def test_registry_list_all():
    reg: Registry = Registry("test")

    @reg.register("a")
    class A:
        pass

    @reg.register("b")
    class B:
        pass

    assert "a" in reg.list_all()
    assert "b" in reg.list_all()
    assert len(reg.list_all()) == 2


def test_registry_overwrite_warning(caplog):
    reg: Registry = Registry("test")

    @reg.register("key")
    class A:
        pass

    @reg.register("key")
    class B:
        pass

    assert "Overwriting already registered item" in caplog.text
    assert reg.get("key") == B


def test_registry_discover_single_module():
    reg: Registry = Registry("test")
    # This should log and return None without crashing
    reg.discover("agentauth.main")
    assert reg.list_all() == {}
