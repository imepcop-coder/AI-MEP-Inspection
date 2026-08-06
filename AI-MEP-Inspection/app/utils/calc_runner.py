import logging
import traceback
from typing import Any, Callable, Dict

logger = logging.getLogger('ai_mep.calc')


def run_calculation(calc_name: str, page: Dict[str, Any] | None, func: Callable[..., Any], inputs: Dict[str, Any]):
    """
    Run a calculation with structured logging and safe error handling.
    Returns a dict with keys: success (bool), result (dict|any), error (str|None), exc_info (str|None), inputs
    """
    log_ctx = {
        'calculator': calc_name,
        'inputs_received': inputs,
    }
    logger.info("Calculation Started: %s", calc_name, extra={'calc': log_ctx})
    try:
        logger.debug("Validated inputs for %s: %s", calc_name, inputs)
        result = func(**inputs) if callable(func) else func(inputs)
        # Some calculation functions may return objects with dict(); normalize
        if hasattr(result, 'dict'):
            result_obj = result.dict()
        else:
            result_obj = result
        if result_obj is None:
            raise RuntimeError('Calculation returned None')
        logger.info("Calculation Completed: %s", calc_name, extra={'calc': log_ctx})
        return {
            'success': True,
            'result': result_obj,
            'error': None,
            'exc_info': None,
            'inputs': inputs,
        }
    except Exception as ex:
        tb = traceback.format_exc()
        logger.exception("Calculation Failed: %s -- %s", calc_name, str(ex), extra={'calc': log_ctx})
        # preserve stack trace in returned structure for server logs; not sent to users
        return {
            'success': False,
            'result': None,
            'error': str(ex),
            'exc_info': tb,
            'inputs': inputs,
        }
