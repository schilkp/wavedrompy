import re

import xmldiff
import xmldiff.main
from attrdict import AttrDict
from lxml import etree


def main(f_out, f_out_py):
    parser = etree.XMLParser(remove_blank_text=True)
    orig_tree = etree.parse(f_out, parser)
    py_tree = etree.parse(f_out_py, parser)

    diff = xmldiff.main.diff_trees(orig_tree, py_tree)
    unknown = []

    for action in diff:
        if isinstance(action, xmldiff.actions.UpdateAttrib):
            node = orig_tree.xpath(action.node)[0]
            if node.tag[-3:] == "svg" and action.name == "viewBox":
                # The viewBox format differs, both are legal notations (space vs. comma-separated)
                if re.sub(r"\s+", ",", node.attrib[action.name]) == action.value:
                    continue
            elif re.sub(r"\s+", "", node.attrib[action.name]) == re.sub(r"\s+", "", action.value):
                # Whitespace differences are okay
                continue
            elif action.name == "transform" and re.match(r"translate\(.*\)", action.value):
                # Float vs. int in attribute
                match_py = re.match(r"translate\((\d+(?:\.\d+)?)(?:\s*[\s,]\s*(\d+(?:\.\d+)?))?\)", action.value)
                py = AttrDict({"x": match_py[1], "y": match_py[2]})
                match_js = re.match(r"translate\((\d+(?:\.\d+)?)(?:\s*[\s,]\s*(\d+(?:\.\d+)?))?\)", node.attrib["transform"])
                js = AttrDict({"x": match_js[1], "y": match_js[2]})
                if float(py.x) == float(js.x) and (py.y is None or py.y == js.y):
                    continue
        elif isinstance(action, xmldiff.actions.InsertAttrib):
            node = orig_tree.xpath(action.node)[0]
            if node.tag[-3:] == "svg" and action.name in ["baseProfile", "version"]:
                # svgwrite adds more info to the svg element
                continue
        elif isinstance(action, xmldiff.actions.MoveNode):
            frm = orig_tree.xpath(action.node)[0].getparent()
            target = orig_tree.xpath(action.target)[0]
            okay = False
            if frm == target:
                # As long as we move in the same node everything is fine
                okay = True
            # But we need to patch anyways, to avoid later errors
            node = orig_tree.xpath(action.node)[0]
            node.getparent().remove(node)
            target = orig_tree.xpath(action.target)[0]
            target.insert(action.position, node)
            if okay:
                continue
        elif isinstance(action, xmldiff.actions.UpdateTextIn):
            node = orig_tree.xpath(action.node)[0]
            if action.text is None:
                if node.tag[-2:] == "}g" and node.attrib["id"] == "groups_0":
                    # Upstream bug, reported: https://github.com/wavedrom/wavedrom/issues/251
                    continue
            elif node.text is None:
                pass
            elif re.sub(r"\s+", "", node.text) == re.sub(r"\s+", "", action.text):
                # Whitespace differences are okay
                continue
            action = action._replace(node=etree.tostring(node))
        elif isinstance(action, xmldiff.actions.InsertNode):
            # Not okay, but we must do the same to preserve the valid tree for further checks
            target = orig_tree.xpath(action.target)[0]
            node = target.makeelement(action.tag)
            target.insert(action.position, node)
            action = action._replace(target=etree.tostring(orig_tree.xpath(action.target)[0]))

        unknown.append(action)
    return unknown