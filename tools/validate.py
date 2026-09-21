#!/usr/bin/env python3
"""按 spec/schema.json 校验界面图样（零依赖，只用标准库）。

用法：
    python3 tools/validate.py spec/examples/*.json

这是一个**最小 JSON Schema 解释器**（只实现本规范用到的那部分关键字），
好处是：规则只有一份（schema.json），校验器不复制规则，两者不会走偏。
编译器写好后，这一步会并进编译器（`cercis-ui compile --check`）。
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "spec" / "schema.json"


class Invalid(Exception):
    def __init__(self, path, message):
        super().__init__(f"{path or '<根>'}：{message}")
        self.path = path


def resolve_ref(schema, root):
    ref = schema["$ref"]
    if not ref.startswith("#/"):
        raise Invalid("", f"仅支持本地引用，遇到 {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def type_ok(value, expected):
    return {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }[expected](value)


def validate(value, schema, root, path=""):
    if "$ref" in schema:
        return validate(value, resolve_ref(schema, root), root, path)

    if "const" in schema and value != schema["const"]:
        raise Invalid(path, f"应为 {schema['const']!r}，实际是 {value!r}")

    if "enum" in schema and value not in schema["enum"]:
        raise Invalid(path, f"应为 {schema['enum']} 之一，实际是 {value!r}")

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(type_ok(value, t) for t in types):
            raise Invalid(path, f"类型应为 {types}，实际是 {type(value).__name__}")

    if isinstance(value, str) and "pattern" in schema:
        if not re.search(schema["pattern"], value):
            raise Invalid(path, f"格式不符：{value!r} 需匹配 {schema['pattern']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise Invalid(path, f"不能小于 {schema['minimum']}，实际 {value}")
        if "maximum" in schema and value > schema["maximum"]:
            raise Invalid(path, f"不能大于 {schema['maximum']}，实际 {value}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise Invalid(path, f"必须大于 {schema['exclusiveMinimum']}，实际 {value}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise Invalid(path, f"至少要有 {schema['minItems']} 项，实际 {len(value)} 项")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise Invalid(path, f"最多 {schema['maxItems']} 项，实际 {len(value)} 项")
        if "items" in schema:
            for i, item in enumerate(value):
                validate(item, schema["items"], root, f"{path}[{i}]")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise Invalid(path, f"缺少必填字段 {key}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    raise Invalid(path, f"不认识的字段 {key}（规范里没有这个）")
        for key, sub in props.items():
            if key in value:
                validate(value[key], sub, root, f"{path}.{key}" if path else key)
        if "propertyNames" in schema:
            for key in value:
                validate(key, schema["propertyNames"], root, f"{path}.<键名>")

    if "oneOf" in schema:
        # 带 type 字段的节点是"可判别"的：直接找对应形态，报错才看得懂
        if isinstance(value, dict) and isinstance(value.get("type"), str):
            matched = [
                c
                for c in schema["oneOf"]
                if branch_const(c, root) == value["type"]
            ]
            if len(matched) == 1:
                validate(value, matched[0], root, path)
                return
            if not matched:
                known = [branch_const(c, root) for c in schema["oneOf"]]
                raise Invalid(
                    path, f"未知的组件类型 {value['type']!r}（可用：{', '.join(k for k in known if k)}）"
                )

        errors = []
        for candidate in schema["oneOf"]:
            try:
                validate(value, candidate, root, path)
                return
            except Invalid as e:
                errors.append(str(e))
        joined = "\n    - ".join(errors)
        raise Invalid(path, f"不符合任何一个允许的形态：\n    - {joined}")

    if "allOf" in schema:
        for candidate in schema["allOf"]:
            validate(value, candidate, root, path)


def branch_const(candidate, root):
    """取出某个候选形态的 type 常量（用于按判别字段挑选分支）。"""
    seen = 0
    while "$ref" in candidate and seen < 10:
        candidate = resolve_ref(candidate, root)
        seen += 1
    return candidate.get("properties", {}).get("type", {}).get("const")


def main(argv):
    files = argv[1:]
    if not files:
        print(__doc__)
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    failed = 0
    for name in files:
        path = Path(name)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            validate(data, schema, schema)
            print(f"✓ {path} 通过（{count_nodes(data)} 个组件）")
        except json.JSONDecodeError as e:
            failed += 1
            print(f"✗ {path} 不是合法 JSON：{e}")
        except Invalid as e:
            failed += 1
            print(f"✗ {path}\n    {e}")
    return 1 if failed else 0


def count_nodes(value):
    """数一数图样里有多少个组件（带 type 字段的对象）。"""
    if isinstance(value, list):
        return sum(count_nodes(v) for v in value)
    if isinstance(value, dict):
        own = 1 if "type" in value and isinstance(value["type"], str) else 0
        return own + sum(count_nodes(v) for v in value.values())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
