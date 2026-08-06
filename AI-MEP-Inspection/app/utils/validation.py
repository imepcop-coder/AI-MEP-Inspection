from typing import List, Dict, Any


def _label_for_field(page: dict, field_name: str) -> str:
    # Search page fields for label
    if not page:
        return field_name.replace('_', ' ').title()
    for f in page.get('fields', []):
        if f.get('name') == field_name:
            return f.get('label', field_name.replace('_', ' ').title())
    # Fallback
    return field_name.replace('_', ' ').title()


def map_pydantic_errors(page: dict, errors: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Convert pydantic ValidationError.errors() into a mapping of field_name -> user-friendly message.
    - page: calculator page dict (used to get field labels)
    - errors: list returned by ValidationError.errors()
    Returns: dict mapping field names to human-readable messages.
    """
    mapped: Dict[str, str] = {}

    for err in errors:
        loc = err.get('loc', [])
        msg = err.get('msg', '')
        err_type = err.get('type', '')
        ctx = err.get('ctx') or {}

        # Determine field name from loc
        field_name = None
        if isinstance(loc, (list, tuple)) and len(loc) > 0:
            # loc may be e.g. ('body', 'field') or ('field',)
            if len(loc) == 1:
                field_name = str(loc[0])
            else:
                # try to find the first string that isn't 'body'
                for part in loc:
                    if isinstance(part, str) and part != 'body':
                        field_name = part
                        break
        if not field_name:
            # fallback to a generic field key
            field_name = (loc[-1] if isinstance(loc, (list, tuple)) else str(loc))

        label = _label_for_field(page, field_name)

        # Map common error types to friendly messages
        message = None
        if err_type and ('missing' in err_type or 'required' in err_type):
            message = f"{label} is required."
        elif 'type_error' in err_type or 'value_error.number' in err_type or 'value_error.float' in err_type:
            message = f"{label} must be a valid number."
        elif 'value_error' in err_type:
            # handle inequalities via ctx
            if ctx.get('limit_value') is not None:
                limit = ctx.get('limit_value')
                if 'ge' in err_type or 'not_ge' in err_type or 'greater_than' in err_type:
                    message = f"{label} must be greater than or equal to {limit}."
                elif 'le' in err_type or 'not_le' in err_type or 'less_than' in err_type:
                    message = f"{label} must be less than or equal to {limit}."
            else:
                # use the original message but sanitize
                message = f"{label}: {msg}"
        else:
            # fallback: sanitize pydantic msg
            # avoid leaking internal names: show label + brief message
            if 'ensure this value' in msg:
                message = f"{label} {msg.replace('ensure this value ', '')}"
            else:
                message = f"{label}: {msg}"

        # final safety: ensure message is not None
        if not message:
            message = f"{label}: Invalid value."

        mapped[str(field_name)] = message

    return mapped
