# app/agent/tools/vision.py
from app.agent.tools.base_tool import BaseTool

try:
    import mss
    import mss.tools
    GUI_AVAILABLE = True
except (ImportError, KeyError, OSError):
    mss = None
    GUI_AVAILABLE = False

class _UnavailableTool(BaseTool):
    """A placeholder for a tool that is not available in the current environment."""
    _description = "This tool is not available in the current environment."
    @property
    def description(self):
        return self._description

    def execute(self, *args, **kwargs):
        return self._safe_execute(lambda: (_ for _ in ()).throw(Exception(self._description)))

if GUI_AVAILABLE:
    from PIL import Image
    import pytesseract

    class ScreenshotTool(BaseTool):
        """
        Takes a screenshot of the entire screen and saves it to a file.
        Example: `take_screenshot(filename='screenshot.png')`
        """
        def execute(self, filename: str = "screenshot.png"):
            def _take_screenshot():
                with mss.mss() as sct:
                    # Use the first monitor
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    # Create an Image
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                    img.save(filename)
                return f"Screenshot saved to '{filename}'."
            return self._safe_execute(_take_screenshot)

    class AnalyzeScreenOCRTool(BaseTool):
        """
        Analyzes the screen using OCR to find text and its coordinates.
        Returns a list of objects, each containing the text and its bounding box.
        Example: `[{"text": "File", "box": [50, 20, 100, 40]}]`
        """
        def execute(self):
            def _analyze_screen():
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

                    # Use pytesseract to get OCR data with bounding boxes
                    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)

                    results = []
                    for i in range(len(data['text'])):
                        text = data['text'][i].strip()
                        if text: # Only add non-empty text
                            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                            results.append({
                                "text": text,
                                "box": [x, y, x + w, y + h] # [left, top, right, bottom]
                            })
                    return results
            return self._safe_execute(_analyze_screen)

else:
    class ScreenshotTool(_UnavailableTool):
        _description = "Screen capture is not available in this environment."
    class AnalyzeScreenOCRTool(_UnavailableTool):
        _description = "Screen analysis is not available in this environment."
