from typing import Any


def mask_sensitive_data(data: Any, sensitive_keys: set[str] | None = None) -> Any:
    """Recursively mask sensitive keys in a dictionary or list.

    Default sensitive keys include 'api_key', 'secret', 'password', 'token', 'key'.
    """
    if sensitive_keys is None:
        sensitive_keys = {"api_key", "secret", "password", "token"}

    if isinstance(data, dict):
        masked_dict = {}
        for k, v in data.items():
            k_lower = k.lower()
            # Mask if any sensitive key is a substring or if it matches 'key' exactly
            if any(sk in k_lower for sk in sensitive_keys) or k_lower == "key":
                masked_dict[k] = "********"
            else:
                masked_dict[k] = mask_sensitive_data(v, sensitive_keys)
        return masked_dict
    elif isinstance(data, (list, tuple, set)):
        return [mask_sensitive_data(item, sensitive_keys) for item in data]
    return data
