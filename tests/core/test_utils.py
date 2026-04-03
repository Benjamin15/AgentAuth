from agentauth.core.utils import mask_sensitive_data


def test_data_masking_base():
    data = {"api_key": "sk-12345", "name": "Test Agent"}
    masked = mask_sensitive_data(data)
    assert masked["api_key"] == "********"
    assert masked["name"] == "Test Agent"


def test_mask_sensitive_data_custom_keys():
    data = {"secret_id": "123", "public": "abc"}
    masked = mask_sensitive_data(data, sensitive_keys={"secret"})
    assert masked["secret_id"] == "********"
    assert masked["public"] == "abc"


def test_mask_recursive_dict():
    data = {"user": {"password": "pwd", "email": "a@b.com"}}
    masked = mask_sensitive_data(data)
    assert masked["user"]["password"] == "********"
    assert masked["user"]["email"] == "a@b.com"


def test_mask_list_and_types():
    data = [{"token": "t1"}, {"other": "o1"}]
    masked = mask_sensitive_data(data)
    assert masked[0]["token"] == "********"
    # Test tuples and sets conversions to list
    data_tuple = ({"key": "k1"},)
    masked_tuple = mask_sensitive_data(data_tuple)
    assert masked_tuple[0]["key"] == "********"


def test_mask_key_exact_match():
    # 'key' should be masked exactly too
    assert mask_sensitive_data({"key": "val"})["key"] == "********"


def test_mask_non_dict_return():
    assert mask_sensitive_data(123) == 123
    assert mask_sensitive_data("string") == "string"
