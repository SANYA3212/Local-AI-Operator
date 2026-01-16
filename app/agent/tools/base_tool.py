# app/agent/tools/base_tool.py
import json

class BaseTool:
    """Base class for all tools."""

    def execute(self, *args, **kwargs):
        """
        Executes the tool with given arguments and returns a structured result.
        This method should be overridden by subclasses.
        """
        raise NotImplementedError

    def _safe_execute(self, func, *args, **kwargs):
        """
        A wrapper to safely execute the tool's main logic, ensuring a structured
        JSON output and handling exceptions.
        """
        try:
            result = func(*args, **kwargs)
            return json.dumps({
                "status": "success",
                "data": result
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": str(e)
            })

    @property
    def description(self):
        """
        Returns a description of the tool from its docstring.
        """
        return self.__doc__ or self.__class__.__name__
