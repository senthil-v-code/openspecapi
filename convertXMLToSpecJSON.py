# Re-import necessary libraries after kernel reset
import xml.etree.ElementTree as ET
import json

# Re-define functions after reset
def extract_regexes(root):
    return {r.get("name"): r.get("value") for r in root.findall(".//regexes/regex")}

def extract_template_definitions(root, regex_map):
    templates = {}

    def build_schema(template_element):
        properties = {}
        for key in template_element.findall('key'):
            key_name = key.get('name') or "item"
            prop = {
                "type": key.get('type', 'string').lower(),
                "description": key.get('description', '')
            }
            if key.get('max-len'):
                prop["maxLength"] = int(key.get('max-len'))
            if key.get('min-len'):
                prop["minLength"] = int(key.get('min-len'))
            if key.get('regex'):
                pattern_key = key.get('regex')
                prop["pattern"] = regex_map.get(pattern_key, pattern_key)
            if key.get('min-occurrences') == '1':
                prop["minOccurs"] = 1
            if key.get('template'):
                ref_template = key.get('template')
                prop["$ref"] = f"#/components/schemas/{ref_template}"
            properties[key_name] = prop
        return {
            "type": "object",
            "properties": properties
        }

    for template in root.findall(".//jsontemplate"):
        name = template.get('name')
        templates[name] = build_schema(template)
    return templates

def create_openapi_spec(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    regex_map = extract_regexes(root)
    json_templates = extract_template_definitions(root, regex_map)

    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": root.get('name'),
            "version": "1.0.0",
            "description": "API specification for " + root.get('name')
        },
        "servers": [
            {
                "url": "https://api.example.com",
                "description": "API Server"
            }
        ],
        "paths": {},
        "components": {
            "schemas": json_templates,
            "securitySchemes": {
                "OAuth2": {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "https://example.com/oauth/authorize",
                            "scopes": {
                                "messages": "Access to messages",
                                "organizations": "Access to organization data"
                            }
                        }
                    }
                }
            }
        }
    }

    for url in root.findall('.//urls/url'):
        path = url.get('path')
        method = url.get('method').lower()

        if path not in openapi_spec["paths"]:
            openapi_spec["paths"][path] = {}
        
        oauthscope_raw = url.get('oauthscope')
        scope = "default"
        if oauthscope_raw:
            scopes_list = [s.strip() for s in oauthscope_raw.split(',') if s.strip()]
            if scopes_list:
                scope = scopes_list[0]

        operation = {
            "summary": url.get('description', ''),
            "tags": [scope],
            "security": [{"OAuth2": [scope]}] if oauthscope_raw else [],
            "responses": {
                "200": {
                    "description": "Successful operation",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object"
                            }
                        }
                    }
                }
            }
        }

        parameters = []
        for param in url.findall('param'):
            param_type = param.get('type', 'string').lower()
            if param_type == 'jsonobject':
                continue

            schema = {"type": param_type}
            if param.get("regex"):
                schema["pattern"] = regex_map.get(param.get("regex"), param.get("regex"))

            parameters.append({
                "name": param.get('name'),
                "in": "query" if method in ["get", "delete"] else "path",
                "description": param.get('description', ''),
                "required": param.get('min-occurrences') == "1",
                "schema": schema
            })

        if parameters:
            operation["parameters"] = parameters

        if method in ['post', 'put', 'patch', 'delete']:
            inputstream = url.find('inputstream')
            if inputstream is not None and inputstream.get('template'):
                template_name = inputstream.get('template')
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{template_name}"
                            }
                        }
                    }
                }

        openapi_spec["paths"][path][method] = operation

    return openapi_spec

# Reprocess the uploaded XML
xml_path = "security.xml"
spec = create_openapi_spec(xml_path)
output_path = "openapi_with_regex_patterns.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2, ensure_ascii=False)
