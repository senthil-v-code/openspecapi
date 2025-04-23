# Re-import necessary libraries after kernel reset
import xml.etree.ElementTree as ET
import json
import requests
from genson import SchemaBuilder
import re

WIREMOCK_URL = "http://localhost:9120"

def generate_json_schema(json_data):
    builder = SchemaBuilder()
    builder.add_object(json_data)
    return builder.to_schema()

def to_pascal_case(s):
    words = re.split(r'[\s_\-]+', s)
    return ''.join(word.capitalize() for word in words)

# Re-define functions after reset
def extract_regexes(root):
    return {r.get("name"): r.get("value") for r in root.findall(".//regexes/regex")}

def extract_throttling(url_element):
    throttles = []
    for throttle in url_element.findall('throttle'):
        duration = throttle.get('duration')
        lock_period = throttle.get('lock-period')
        threshold = throttle.get('threshold')
        throttles.append({
            "duration": duration,
            "lockPeriod": lock_period,
            "threshold": int(threshold)
        })
    return throttles

def extract_template_definitions(root, regex_map):
    templates = {}

    def build_schema(template_element):
        properties = {}
        required = []
        for key in template_element.findall('key'):
            key_name = key.get('name') or "item"
            type = key.get('type', 'string')
            if(type=="int"):
                type = "integer"
            elif(type=="long"):
                type = "number"
            elif(type=="String"):
                type = "string"
            prop = {
                "type": type,
                "description": key.get('description', '')
            }
            required = []
            max_len_value = key.get('max-len')
            if max_len_value is not None and type=="string":
                prop["maxLength"] = int(key.get('max-len'))
            
            min_len_value = key.get('min-len')
            if min_len_value is not None and type=="string":
                prop["minLength"] = int(key.get('min-len'))
            if key.get('regex'):
                pattern_key = key.get('regex')
                prop["pattern"] = regex_map.get(pattern_key, pattern_key)
            if key.get('min-occurrences') == '1':
                required.append(key_name)
            if key.get('template'):
                ref_template = key.get('template')
                prop["$ref"] = f"#/components/schemas/{ref_template}"
            properties[key_name] = prop
        schema = {
            "type": "object",
            "properties": properties
        }

        if required:
            schema["required"] = required

        return schema

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
            "description": """ ZohoIM abstracts the difficulties in integrating various Instant Messaging Channels by Providing an Unified API.
                ### Communicate with your customers through any Instant Messaging Channel
                <img src="https://content.pstmn.io/001c6190-9c45-4b0f-87cb-6c1043f209cd/aW1hZ2UucG5n" /> <br><br><br>
                
                **Why Zoho IM?**
                Most of the support channels often bring layers of complexities - IM manages all these interactions into a single connected system.
                Our focus was on improving agent productivity with an intuitive approach and compatible interface.
                Our seamless integration with customers' best-loved platforms such as WhatsApp, Telegram, LINE, WeChat and Facebook Messenger.
                <br><br>
                **Getting Started** <br>
                - All Zoho IM APIs require these two mandatory fields in the header. <br>
                - Authorization - Authentication request token <br>
                - orgId -ID of the organization to access. All API endpoints except /organizations mandatorily require the orgId. <br>

                
                <img src="https://content.pstmn.io/7ba8a04d-b133-46e2-8d4c-633a5bc57378/ZXpnaWYuY29tLXZpZGVvLXRvLWdpZiAoMSkuZ2lm" /> <br><br>
                For detailed flow of Authorization [visit](https://www.zoho.com/accounts/protocol/oauth/self-client/authorization-code-flow.html)
                <br><br>
                **Steps (refer the above gif):** <br>
                - Sign into https://www.accounts.zoho.com <br>
                - Go to [Zoho Developer Console](https://api-console.zoho.com/) -> Add Client <br>
                - Choose Self Client  <br>
                - Note down Client ID and Client Secret under Client Secret Tab <br>
                - Under Generate Code - Provide scopes, time duration and desciption  <br>
                - Choose create which will provide a code.  <br>
                <br><br>
                **Scopes:** <br>
                - ZohoIM.organizations.ALL <br>
                - ZohoIM.channels.ALL <br>
                - ZohoIM.conversations.ALL  <br>
                - ZohoIM.messages.ALL <br>
                - ZohoIM.bots.ALL <br>
                - ZohoIM.users.ALL  <br>
                - ZohoIM.contacts.ALL <br>
                - ZohoIM.search.READ  <br>
                <br><br>
                **Note:**
                - Access token should be prefixed with the prefix "Zoho-oauthtoken" <br>
                    Example token, **Zoho-oauthtoken 1000.dfe95e72e98e1657****  """
        },
        "servers": [
            {
                "url": "https://im.localzoho.com",
                "description": "Local Zoho Server"
            },
            {
                "url": "http://127.0.0.1:3000",
                "description": "Mock Server"
            }
        ],
        "paths": {},
        "components": {
            "schemas": json_templates,
            "parameters":{
                "orgId":{
                    "in": "header",
                    "name": "orgId",
                    "schema":{
                        "type": "string"
                    },
                    "example": "85273209",
                    "required": True
                },
                "service":{
                    "in": "header",
                    "name": "service",
                    "schema":{
                        "type": "string",
                    },
                    "example": "ZOHO_DESK"
                },
                "serviceOrgId":{
                    "in": "header",
                    "name": "serviceOrgId",
                    "schema":{
                        "type": "string",
                    },
                    "example": "71923149"
                }
            },
            "securitySchemes": {
                "OAuth2": {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "https://example.com/oauth/authorize",
                            "scopes": {
                                "ZohoIM.messages.ALL": "Access to messages",
                                "ZohoIM.organizations.ALL": "Access to organization data",
                                "ZohoIM.channels.ALL":"Access to organization data",
                                "ZohoIM.contacts.ALL":"Access to Contacts data",
                                "ZohoIM.conversations.ALL":"Access to Conversation data",
                                "ZohoIM.users.ALL":"Access to Users data"   
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
        
        tag = "default"
        if("api/v1/" in path):
            tag = path.split("/")[3]
        else:
            tag = path.split("/")[1]

        tag = to_pascal_case(tag)
        
        oauthscope_raw = url.get('oauthscope')
        scope = "default"
        
        if oauthscope_raw:
            scopes_list = [s.strip() for s in oauthscope_raw.split(',') if s.strip()]
            scopes = [f"ZohoIM.{scope}.ALL" for scope in scopes_list]
        operation = {
            "summary": url.get('description', ''),
            "tags": [tag],
            "security": [{"OAuth2": scopes}] if oauthscope_raw else [],
            "responses": {
                "200": {
                    "description": "Successful operation",
                    "content": {
                        "application/json": {
                            "schema": {"type": "object"}
                        }
                    }
                }
            }
        }

        parameters = []
        parameters.append({"$ref": "#/components/parameters/service"})
        parameters.append({"$ref": "#/components/parameters/serviceOrgId"})
        parameters.append({"$ref": "#/components/parameters/orgId"})
        for param in url.findall('param'):
            param_type = param.get('type', 'string').lower()
            if(param_type=="int"):
                param_type = "integer"
            elif(param_type=="long"):
                param_type = "number"
            elif(param_type=="String"):
                param_type = "string"
            if param_type == 'jsonobject':
                continue

            schema = {"type": param_type}
            if param.get("regex"):
                schema["pattern"] = regex_map.get(param.get("regex"), param.get("regex"))

            parameters.append({
                "name": param.get('name'),
                "in": "query" if method in ["get", "delete"] else "path",
                "description": param.get('description', ''),
                "schema": schema
            })
            if(param.get('min-occurrences') == "1"):
              parameters.append({
                "required": param.get('min-occurrences') == "1"
            })
        if parameters:
            operation["parameters"] = parameters
        
        apipath = WIREMOCK_URL + path
        response = requests.request(method, apipath)
        schema = "object"
        if response.status_code == 200:
            response_json = response.json()
            schema = generate_json_schema(response_json)
            operation["responses"]["200"]["content"]["application/json"]["schema"] = schema
            operation["responses"]["200"]["content"]["application/json"]["example"] = response_json
        if path not in openapi_spec["paths"]:
            openapi_spec["paths"][path] = {}
        
        throttling = extract_throttling(url)
        if throttling:
            operation["x-throttling"] = throttling

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
