import xml.etree.ElementTree as ET
from svgpathtools import svg2paths, wsvg, Path, Line, CubicBezier, QuadraticBezier
import json
import os
from collections import Counter

def simplify_svg(paths, attributes, max_layers=40):
    """Simplifies the SVG, prioritizing larger paths, combining similar styles."""
    combined_paths = {}
    for path, attrib in zip(paths, attributes):
        style_key = (attrib.get('fill', '#000000'), attrib.get('opacity', '1'))
        if style_key not in combined_paths:
            combined_paths[style_key] = []
        combined_paths[style_key].append(path)

    simplified_paths = []
    simplified_attributes = []
    for (fill_color, opacity), paths_list in combined_paths.items():
        combined_path = Path()
        for p in paths_list:
             if isinstance(p, Path):
                  for segment in p:
                    combined_path.append(segment)
             else:
                  combined_path.append(p)
        simplified_paths.append(combined_path)
        simplified_attributes.append({'fill': fill_color, 'opacity': opacity})

    if len(simplified_paths) > max_layers:
        path_sizes = []
        for path in simplified_paths:
            if isinstance(path, Path):
                bbox = path.bbox()
                path_sizes.append((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
            else:
                path_sizes.append(0)
        sorted_paths = sorted(zip(simplified_paths, simplified_attributes, path_sizes), key=lambda x: x[2], reverse=True)
        simplified_paths = [path for path, _, _ in sorted_paths[:max_layers]]
        simplified_attributes = [attrib for _, attrib, _ in sorted_paths[:max_layers]]

    if len(simplified_paths) > max_layers:
        combined_paths = {}
        for path, attrib in zip(simplified_paths, simplified_attributes):
            fill_key = attrib.get('fill', '#000000')
            if fill_key not in combined_paths:
                combined_paths[fill_key] = []
            combined_paths[fill_key].append((path, attrib.get('opacity',1)))

        simplified_paths = []
        simplified_attributes = []
        for fill_color, path_opacity_list in combined_paths.items():
             combined_path = Path()
             avg_opacity = 0
             for p, opacity in path_opacity_list:
                if isinstance(p, Path):
                    for segment in p:
                         combined_path.append(segment)
                else:
                    combined_path.append(p)
                avg_opacity+= float(opacity)
             if len(path_opacity_list) > 0:
                 avg_opacity /= len(path_opacity_list)
             simplified_paths.append(combined_path)
             simplified_attributes.append({'fill': fill_color, 'opacity':str(avg_opacity)})

    if len(simplified_paths) > max_layers:
      simplified_paths = simplified_paths[:max_layers]
      simplified_attributes = simplified_attributes[:max_layers]

    return simplified_paths, simplified_attributes


def scale_to_fit(emblem_data, max_dimension=317):
    """Scales the emblem data to fit within the maximum dimension."""

    # Find the maximum top and height values
    max_top = 0
    max_height = 0
    for layer in emblem_data:
        max_top = max(max_top, layer['top'])
        max_height = max(max_height, layer['height'])

    #Calculate overall height.
    overall_height = 0
    for item in emblem_data:
      overall_height = max(overall_height, item["top"] + item["height"])

    # Calculate the scaling factor needed
    scale_factor = 1.0
    if overall_height > max_dimension:
        scale_factor = max_dimension / overall_height

    # Apply the scaling factor to top, left, height, and width
    if scale_factor != 1.0:  #Only scale if necessary.
        for layer in emblem_data:
            layer['top'] *= scale_factor
            layer['left'] *= scale_factor
            layer['height'] *= scale_factor
            layer['width'] *= scale_factor
    return emblem_data


def svg_to_battlefield(svg_filepath, initial_scale_factor=1.6, max_layers=40, max_dimension=317):
    """Converts SVG to Battlefield emblem JSON, scales to fit, simplifies layers."""
    try:
        tree = ET.parse(svg_filepath)
        root = tree.getroot()
        svg_width = float(root.get('width').replace('px', ''))
        svg_height = float(root.get('height').replace('px', ''))

        paths, attributes = svg2paths(svg_filepath)
        paths, attributes = simplify_svg(paths, attributes, max_layers)
        emblem_data = []

        for path, attrib in zip(paths, attributes):
            fill_color = attrib.get('fill', '#000000')
            if fill_color.lower() == 'none':
                fill_color = "#000000"
            opacity = float(attrib.get('opacity', 1))

            if isinstance(path, Path):
                for segment in path:
                    if isinstance(segment, Line):
                        start = segment.start
                        end = segment.end
                        top = min(start.imag, end.imag) * initial_scale_factor
                        left = min(start.real, end.real) * initial_scale_factor
                        height = abs(end.imag - start.imag) * initial_scale_factor
                        width = abs(end.real - start.real) * initial_scale_factor
                        emblem_data.append({
                            "opacity": opacity, "angle": 0, "flipX": False, "flipY": False,
                            "top": top, "left": left, "height": height, "width": width,
                            "asset": "Stroke", "selectable": False, "fill": fill_color
                        })
                    elif isinstance(segment, (CubicBezier, QuadraticBezier)):
                        num_points = 20
                        points = [segment.point(i/num_points) for i in range(num_points + 1)]
                        min_x = min(p.real for p in points) * initial_scale_factor
                        min_y = min(p.imag for p in points) * initial_scale_factor
                        max_x = max(p.real for p in points) * initial_scale_factor
                        max_y = max(p.imag for p in points) * initial_scale_factor
                        emblem_data.append({
                            "opacity": opacity, "angle": 0, "flipX": False, "flipY": False,
                            "top": min_y, "left": min_x, "height": max_y - min_y, "width": max_x - min_x,
                            "asset": "Stroke", "selectable": False, "fill": fill_color
                        })
                    else:
                        print(f"Unsupported segment: {type(segment)}")
                        return None
            elif 'd' not in attrib:
                rect_x = float(attrib.get('x', 0)) * initial_scale_factor
                rect_y = float(attrib.get('y', 0)) * initial_scale_factor
                rect_width = float(attrib.get('width', 0)) * initial_scale_factor
                rect_height = float(attrib.get('height', 0)) * initial_scale_factor
                emblem_data.append({
                    "opacity": opacity, "angle": 0, "flipX": False, "flipY": False,
                    "top": rect_y, "left": rect_x, "height": rect_height, "width": rect_width,
                    "asset": "Square", "selectable": False, "fill": fill_color
                })
            else:
                print(f"Unhandled element: {attrib}")
                return None

        # --- Scale to fit within max_dimension ---
        emblem_data = scale_to_fit(emblem_data, max_dimension)

        if len(emblem_data) > max_layers:
            print(f"Warning: {len(emblem_data)} layers (exceeds {max_layers}).")

        json_data = {
            "jsonrpc": "2.0", "method": "Emblems.newPrivateEmblem",
            "params": {"data": emblem_data}, "id": "00000000-0000-0000-0000-000000000000"
        }
        return json.dumps(json_data, separators=(',', ':'))

    except Exception as e:
        print(f"Error: {e}")
        return None

def generate_js_code(svg_path):
    json_payload = svg_to_battlefield(svg_path)
    return None if not json_payload else f"""var request=new XMLHttpRequest;request.open("POST","https://companion-api.battlefield.com/jsonrpc/web/api?Emblems.newPrivateEmblem",!0),request.onreadystatechange=function(){{if(request.readyState==XMLHttpRequest.DONE){{var e=JSON.parse(request.responseText);if(e.result){{window.location.href=window.location.href.replace("/new","/edit/")+e.result.slot}}else{{alert("Error")}}}}}},request.setRequestHeader("Content-Type","application/json;charset=UTF-8"),request.setRequestHeader("X-GatewaySession",localStorage.gatewaySessionId);var data={json_payload.replace(' ', '')};request.send(JSON.stringify(data));""".replace('\n', '').replace('\r', '')

if __name__ == "__main__":
    svg_file = "your_emblem.svg"
    javascript_code = generate_js_code(svg_file)
    if javascript_code:
        with open("emblem_script.txt", "w") as txt_file:
            txt_file.write(javascript_code)
        print("JavaScript code saved to emblem_script.txt.")
    else:
        print("Failed to generate JavaScript code.")
    input("Press Enter to exit...")
