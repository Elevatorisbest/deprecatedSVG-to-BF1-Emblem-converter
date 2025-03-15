import xml.etree.ElementTree as ET
from svgpathtools import svg2paths, wsvg, Path, Line, CubicBezier, QuadraticBezier
import json
import os  # Import the 'os' module

def svg_to_battlefield(svg_filepath, scale_factor=1.6):
    """
    Converts an SVG file to Battlefield emblem JSON.

    Args:
        svg_filepath: Path to the SVG file.
        scale_factor: Scaling factor (default 1.6 for 320px to 512px).

    Returns:
        A JSON string representing the emblem data.  Returns None on error.
    """
    try:
        tree = ET.parse(svg_filepath)
        root = tree.getroot()

        # Get SVG width and height (important for scaling and positioning)
        svg_width = float(root.get('width').replace('px', ''))
        svg_height = float(root.get('height').replace('px',''))

        paths, attributes = svg2paths(svg_filepath)
        emblem_data = []

        for path, attrib in zip(paths, attributes):
            # --- Fill Color ---
            fill_color = "#000000"  # Default to black
            if 'fill' in attrib:
                fill_color = attrib['fill']
                if fill_color.lower() == 'none':
                    fill_color = "#000000"  # Or handle transparency differently
            elif 'style' in attrib:
                style_parts = attrib['style'].split(';')
                for part in style_parts:
                    if part.startswith('fill:'):
                        fill_color = part.split(':')[1].strip()
                        break
            # --- Opacity ---
            opacity = 1
            if 'opacity' in attrib:
                opacity= float(attrib['opacity'])
            elif 'style' in attrib:
                  style_parts = attrib['style'].split(';')
                  for part in style_parts:
                      if part.startswith('opacity:'):
                          opacity = float(part.split(':')[1].strip())
            # --- Handle different path segments ---
            if isinstance(path, Path):
                for segment in path:
                    if isinstance(segment, Line):
                        # A straight line. We can treat this as a "Stroke"
                        start = segment.start
                        end = segment.end
                        top = min(start.imag, end.imag) * scale_factor
                        left = min(start.real, end.real) * scale_factor
                        height = abs(end.imag - start.imag) * scale_factor
                        width = abs(end.real - start.real) * scale_factor

                         # Calculate the angle of the line
                        angle = 0

                        emblem_data.append({
                            "opacity": opacity,
                            "angle": angle,
                            "flipX": False,
                            "flipY": False,
                            "top": top,
                            "left": left,
                            "height": height,
                            "width": width,
                            "asset": "Stroke",  # Battlefield uses "Stroke"
                            "selectable": False,
                            "fill": fill_color
                        })

                    elif isinstance(segment, (CubicBezier, QuadraticBezier)):
                         #For curved Beziers, we are approximating it.
                        num_points = 20
                        points = [segment.point(i/num_points) for i in range(num_points + 1)]
                        min_x = min(p.real for p in points) * scale_factor
                        min_y = min(p.imag for p in points) * scale_factor
                        max_x = max(p.real for p in points) * scale_factor
                        max_y = max(p.imag for p in points) * scale_factor

                        emblem_data.append({
                                "opacity": opacity,
                                "angle": 0,
                                "flipX": False,
                                "flipY": False,
                                "top": min_y,
                                "left": min_x,
                                "height": max_y - min_y,
                                "width": max_x - min_x,
                                "asset": "Stroke", #Approximation of curved parts
                                "selectable": False,
                                "fill": fill_color
                            })

                    else:
                      print(f"Unsupported segment type: {type(segment)}")
                      return None

            # --- Handle rectangles (<rect>) ---
            elif 'd' not in attrib:
              if 'x' in attrib:
                rect_x = float(attrib['x']) * scale_factor
              else:
                 rect_x = 0.0
              if 'y' in attrib:
                rect_y = float(attrib['y']) * scale_factor
              else:
                rect_y = 0.0

              if 'width' in attrib:
                rect_width = float(attrib['width']) * scale_factor
              else:
                rect_width = 0
              if 'height' in attrib:
                rect_height = float(attrib['height']) * scale_factor
              else:
                rect_height = 0

              emblem_data.append({
                    "opacity": opacity,
                    "angle": 0,  # Handle rotation later
                    "flipX": False,
                    "flipY": False,
                    "top": rect_y,
                    "left": rect_x,
                    "height": rect_height,
                    "width": rect_width,
                    "asset": "Square",
                    "selectable": False,
                    "fill": fill_color
                })


            else:
                print(f"Unhandled SVG element: {attrib}")
                return None

        # Construct the final JSON payload
        json_data = {
            "jsonrpc": "2.0",
            "method": "Emblems.newPrivateEmblem",
            "params": {
                "data": emblem_data
            },
            "id": "00000000-0000-0000-0000-000000000000"
        }
        return json.dumps(json_data, separators=(',', ':'))  # Minify JSON output

    except Exception as e:
        print(f"Error processing SVG: {e}")
        return None

def generate_js_code(svg_path):

    json_payload = svg_to_battlefield(svg_path)
    if json_payload:

      js_code = f"""var request=new XMLHttpRequest;request.open("POST","https://companion-api.battlefield.com/jsonrpc/web/api?Emblems.newPrivateEmblem",!0),request.onreadystatechange=function(){{if(request.readyState==XMLHttpRequest.DONE){{var e=JSON.parse(request.responseText);if(e.result){{window.location.href=window.location.href.replace("/new","/edit/")+e.result.slot}}else{{alert("Error")}}}}}},request.setRequestHeader("Content-Type","application/json;charset=UTF-8"),request.setRequestHeader("X-GatewaySession",localStorage.gatewaySessionId);var data={json_payload.replace(' ', '')};request.send(JSON.stringify(data));"""
      return js_code.replace('\n', '').replace('\r', '')
    else:
        return None

# --- Example Usage ---
if __name__ == "__main__":
    svg_file = "your_emblem.svg"  # Replace with your SVG file
    javascript_code = generate_js_code(svg_file)
    if javascript_code:
        with open("emblem_script.txt", "w") as txt_file:  # Save the code to a .txt file
            txt_file.write(javascript_code)
        print("JavaScript code successfully saved to emblem_script.txt.")
    else:
        print("Failed to generate JavaScript code.")

    input("Press Enter to exit...")  # Wait for user input before closing the console window
