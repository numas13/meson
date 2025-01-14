# SPDX-License-Identifier: Apache-2.0
# Copyright 2019 The Meson development team

# This class contains the basic functionality needed to run any interpreter
# or an interpreter-based tool
from __future__ import annotations

from .. import mparser
from .visitor import AstVisitor

from itertools import zip_longest
import re
import typing as T

arithmic_map = {
    'add': '+',
    'sub': '-',
    'mod': '%',
    'mul': '*',
    'div': '/'
}

class AstPrinter(AstVisitor):
    def __init__(self, indent: int = 2, arg_newline_cutoff: int = 5, update_ast_line_nos: bool = False):
        self.result = ''
        self.indent = indent
        self.arg_newline_cutoff = arg_newline_cutoff
        self.ci = ''
        self.is_newline = True
        self.last_level = 0
        self.curr_line = 1 if update_ast_line_nos else None

    def post_process(self) -> None:
        self.result = re.sub(r'\s+\n', '\n', self.result)

    def append(self, data: str, node: mparser.BaseNode) -> None:
        self.last_level = node.level
        if self.is_newline:
            self.result += ' ' * (node.level * self.indent)
        self.result += data
        self.is_newline = False

    def append_padded(self, data: str, node: mparser.BaseNode) -> None:
        if self.result and self.result[-1] not in [' ', '\n']:
            data = ' ' + data
        self.append(data + ' ', node)

    def newline(self) -> None:
        self.result += '\n'
        self.is_newline = True
        if self.curr_line is not None:
            self.curr_line += 1

    def visit_BooleanNode(self, node: mparser.BooleanNode) -> None:
        self.append('true' if node.value else 'false', node)
        node.lineno = self.curr_line or node.lineno

    def visit_IdNode(self, node: mparser.IdNode) -> None:
        assert isinstance(node.value, str)
        self.append(node.value, node)
        node.lineno = self.curr_line or node.lineno

    def visit_NumberNode(self, node: mparser.NumberNode) -> None:
        self.append(str(node.value), node)
        node.lineno = self.curr_line or node.lineno

    def escape(self, val: str) -> str:
        return val.translate(str.maketrans({'\'': '\\\'',
                                            '\\': '\\\\'}))

    def visit_StringNode(self, node: mparser.StringNode) -> None:
        assert isinstance(node.value, str)
        self.append("'" + self.escape(node.value) + "'", node)
        node.lineno = self.curr_line or node.lineno

    def visit_FormatStringNode(self, node: mparser.FormatStringNode) -> None:
        assert isinstance(node.value, str)
        self.append("f'" + self.escape(node.value) + "'", node)
        node.lineno = self.curr_line or node.lineno

    def visit_MultilineStringNode(self, node: mparser.StringNode) -> None:
        assert isinstance(node.value, str)
        self.append("'''" + node.value + "'''", node)
        node.lineno = self.curr_line or node.lineno

    def visit_FormatMultilineStringNode(self, node: mparser.FormatStringNode) -> None:
        assert isinstance(node.value, str)
        self.append("f'''" + node.value + "'''", node)
        node.lineno = self.curr_line or node.lineno

    def visit_ContinueNode(self, node: mparser.ContinueNode) -> None:
        self.append('continue', node)
        node.lineno = self.curr_line or node.lineno

    def visit_BreakNode(self, node: mparser.BreakNode) -> None:
        self.append('break', node)
        node.lineno = self.curr_line or node.lineno

    def visit_ArrayNode(self, node: mparser.ArrayNode) -> None:
        node.lineno = self.curr_line or node.lineno
        self.append('[', node)
        node.args.accept(self)
        self.append(']', node)

    def visit_DictNode(self, node: mparser.DictNode) -> None:
        node.lineno = self.curr_line or node.lineno
        self.append('{', node)
        node.args.accept(self)
        self.append('}', node)

    def visit_OrNode(self, node: mparser.OrNode) -> None:
        node.left.accept(self)
        self.append_padded('or', node)
        node.lineno = self.curr_line or node.lineno
        node.right.accept(self)

    def visit_AndNode(self, node: mparser.AndNode) -> None:
        node.left.accept(self)
        self.append_padded('and', node)
        node.lineno = self.curr_line or node.lineno
        node.right.accept(self)

    def visit_ComparisonNode(self, node: mparser.ComparisonNode) -> None:
        node.left.accept(self)
        self.append_padded(node.ctype, node)
        node.lineno = self.curr_line or node.lineno
        node.right.accept(self)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode) -> None:
        node.left.accept(self)
        self.append_padded(arithmic_map[node.operation], node)
        node.lineno = self.curr_line or node.lineno
        node.right.accept(self)

    def visit_NotNode(self, node: mparser.NotNode) -> None:
        node.lineno = self.curr_line or node.lineno
        self.append_padded('not', node)
        node.value.accept(self)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode) -> None:
        node.lineno = self.curr_line or node.lineno
        for i in node.lines:
            i.accept(self)
            self.newline()

    def visit_IndexNode(self, node: mparser.IndexNode) -> None:
        node.iobject.accept(self)
        node.lineno = self.curr_line or node.lineno
        self.append('[', node)
        node.index.accept(self)
        self.append(']', node)

    def visit_MethodNode(self, node: mparser.MethodNode) -> None:
        node.lineno = self.curr_line or node.lineno
        node.source_object.accept(self)
        self.append('.' + node.name.value + '(', node)
        node.args.accept(self)
        self.append(')', node)

    def visit_FunctionNode(self, node: mparser.FunctionNode) -> None:
        node.lineno = self.curr_line or node.lineno
        self.append(node.func_name.value + '(', node)
        node.args.accept(self)
        self.append(')', node)

    def visit_AssignmentNode(self, node: mparser.AssignmentNode) -> None:
        node.lineno = self.curr_line or node.lineno
        self.append(node.var_name.value + ' = ', node)
        node.value.accept(self)

    def visit_PlusAssignmentNode(self, node: mparser.PlusAssignmentNode) -> None:
        node.lineno = self.curr_line or node.lineno
        self.append(node.var_name.value + ' += ', node)
        node.value.accept(self)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode) -> None:
        node.lineno = self.curr_line or node.lineno
        self.append_padded('foreach', node)
        self.append_padded(', '.join(varname.value for varname in node.varnames), node)
        self.append_padded(':', node)
        node.items.accept(self)
        self.newline()
        node.block.accept(self)
        self.append('endforeach', node)

    def visit_IfClauseNode(self, node: mparser.IfClauseNode) -> None:
        node.lineno = self.curr_line or node.lineno
        prefix = ''
        for i in node.ifs:
            self.append_padded(prefix + 'if', node)
            prefix = 'el'
            i.accept(self)
        if not isinstance(node.elseblock, mparser.EmptyNode):
            self.append('else', node)
            node.elseblock.accept(self)
        self.append('endif', node)

    def visit_UMinusNode(self, node: mparser.UMinusNode) -> None:
        node.lineno = self.curr_line or node.lineno
        self.append_padded('-', node)
        node.value.accept(self)

    def visit_IfNode(self, node: mparser.IfNode) -> None:
        node.lineno = self.curr_line or node.lineno
        node.condition.accept(self)
        self.newline()
        node.block.accept(self)

    def visit_TernaryNode(self, node: mparser.TernaryNode) -> None:
        node.lineno = self.curr_line or node.lineno
        node.condition.accept(self)
        self.append_padded('?', node)
        node.trueblock.accept(self)
        self.append_padded(':', node)
        node.falseblock.accept(self)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode) -> None:
        node.lineno = self.curr_line or node.lineno
        break_args = (len(node.arguments) + len(node.kwargs)) > self.arg_newline_cutoff
        for i in node.arguments + list(node.kwargs.values()):
            if not isinstance(i, (mparser.ElementaryNode, mparser.IndexNode)):
                break_args = True
        if break_args:
            self.newline()
        for i in node.arguments:
            i.accept(self)
            self.append(', ', node)
            if break_args:
                self.newline()
        for key, val in node.kwargs.items():
            key.accept(self)
            self.append_padded(':', node)
            val.accept(self)
            self.append(', ', node)
            if break_args:
                self.newline()
        if break_args:
            self.result = re.sub(r', \n$', '\n', self.result)
        else:
            self.result = re.sub(r', $', '', self.result)

class RawPrinter(AstVisitor):

    def __init__(self):
        self.result = ''

    def visit_default_func(self, node: mparser.BaseNode):
        self.result += node.value
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_unary_operator(self, node: mparser.UnaryOperatorNode):
        node.operator.accept(self)
        node.value.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_binary_operator(self, node: mparser.BinaryOperatorNode):
        node.left.accept(self)
        node.operator.accept(self)
        node.right.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_BooleanNode(self, node: mparser.BooleanNode) -> None:
        self.result += 'true' if node.value else 'false'
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_NumberNode(self, node: mparser.NumberNode) -> None:
        self.result += node.raw_value
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_StringNode(self, node: mparser.StringNode) -> None:
        self.result += f"'{node.raw_value}'"
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_MultilineStringNode(self, node: mparser.MultilineStringNode) -> None:
        self.result += f"'''{node.value}'''"
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_FormatStringNode(self, node: mparser.FormatStringNode) -> None:
        self.result += 'f'
        self.visit_StringNode(node)

    def visit_MultilineFormatStringNode(self, node: mparser.MultilineFormatStringNode) -> None:
        self.result += 'f'
        self.visit_MultilineStringNode(node)

    def visit_ContinueNode(self, node: mparser.ContinueNode) -> None:
        self.result += 'continue'
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_BreakNode(self, node: mparser.BreakNode) -> None:
        self.result += 'break'
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_ArrayNode(self, node: mparser.ArrayNode) -> None:
        node.lbracket.accept(self)
        node.args.accept(self)
        node.rbracket.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_DictNode(self, node: mparser.DictNode) -> None:
        node.lcurl.accept(self)
        node.args.accept(self)
        node.rcurl.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_ParenthesizedNode(self, node: mparser.ParenthesizedNode) -> None:
        node.lpar.accept(self)
        node.inner.accept(self)
        node.rpar.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_OrNode(self, node: mparser.OrNode) -> None:
        self.visit_binary_operator(node)

    def visit_AndNode(self, node: mparser.AndNode) -> None:
        self.visit_binary_operator(node)

    def visit_ComparisonNode(self, node: mparser.ComparisonNode) -> None:
        self.visit_binary_operator(node)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode) -> None:
        self.visit_binary_operator(node)

    def visit_NotNode(self, node: mparser.NotNode) -> None:
        self.visit_unary_operator(node)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode) -> None:
        if node.pre_whitespaces:
            node.pre_whitespaces.accept(self)
        for i in node.lines:
            i.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_IndexNode(self, node: mparser.IndexNode) -> None:
        node.iobject.accept(self)
        node.lbracket.accept(self)
        node.index.accept(self)
        node.rbracket.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_MethodNode(self, node: mparser.MethodNode) -> None:
        node.source_object.accept(self)
        node.dot.accept(self)
        node.name.accept(self)
        node.lpar.accept(self)
        node.args.accept(self)
        node.rpar.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_FunctionNode(self, node: mparser.FunctionNode) -> None:
        node.func_name.accept(self)
        node.lpar.accept(self)
        node.args.accept(self)
        node.rpar.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_AssignmentNode(self, node: mparser.AssignmentNode) -> None:
        node.var_name.accept(self)
        node.operator.accept(self)
        node.value.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_PlusAssignmentNode(self, node: mparser.PlusAssignmentNode) -> None:
        node.var_name.accept(self)
        node.operator.accept(self)
        node.value.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode) -> None:
        node.foreach_.accept(self)
        for varname, comma in zip_longest(node.varnames, node.commas):
            varname.accept(self)
            if comma is not None:
                comma.accept(self)
        node.column.accept(self)
        node.items.accept(self)
        node.block.accept(self)
        node.endforeach.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_IfClauseNode(self, node: mparser.IfClauseNode) -> None:
        for i in node.ifs:
            i.accept(self)
        if not isinstance(node.elseblock, mparser.EmptyNode):
            node.elseblock.accept(self)
        node.endif.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_UMinusNode(self, node: mparser.UMinusNode) -> None:
        self.visit_unary_operator(node)

    def visit_IfNode(self, node: mparser.IfNode) -> None:
        node.if_.accept(self)
        node.condition.accept(self)
        node.block.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_ElseNode(self, node: mparser.ElseNode) -> None:
        node.else_.accept(self)
        node.block.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_TernaryNode(self, node: mparser.TernaryNode) -> None:
        node.condition.accept(self)
        node.questionmark.accept(self)
        node.trueblock.accept(self)
        node.column.accept(self)
        node.falseblock.accept(self)
        if node.whitespaces:
            node.whitespaces.accept(self)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode) -> None:
        commas_iter = iter(node.commas)

        for arg in node.arguments:
            arg.accept(self)
            try:
                comma = next(commas_iter)
                comma.accept(self)
            except StopIteration:
                pass

        assert len(node.columns) == len(node.kwargs)
        for (key, val), column in zip(node.kwargs.items(), node.columns):
            key.accept(self)
            column.accept(self)
            val.accept(self)
            try:
                comma = next(commas_iter)
                comma.accept(self)
            except StopIteration:
                pass

        if node.whitespaces:
            node.whitespaces.accept(self)

class AstJSONPrinter(AstVisitor):
    def __init__(self) -> None:
        self.result: T.Dict[str, T.Any] = {}
        self.current = self.result

    def _accept(self, key: str, node: mparser.BaseNode) -> None:
        old = self.current
        data: T.Dict[str, T.Any] = {}
        self.current = data
        node.accept(self)
        self.current = old
        self.current[key] = data

    def _accept_list(self, key: str, nodes: T.Sequence[mparser.BaseNode]) -> None:
        old = self.current
        datalist: T.List[T.Dict[str, T.Any]] = []
        for i in nodes:
            self.current = {}
            i.accept(self)
            datalist += [self.current]
        self.current = old
        self.current[key] = datalist

    def _raw_accept(self, node: mparser.BaseNode, data: T.Dict[str, T.Any]) -> None:
        old = self.current
        self.current = data
        node.accept(self)
        self.current = old

    def setbase(self, node: mparser.BaseNode) -> None:
        self.current['node'] = type(node).__name__
        self.current['lineno'] = node.lineno
        self.current['colno'] = node.colno
        self.current['end_lineno'] = node.end_lineno
        self.current['end_colno'] = node.end_colno

    def visit_default_func(self, node: mparser.BaseNode) -> None:
        self.setbase(node)

    def gen_ElementaryNode(self, node: mparser.ElementaryNode) -> None:
        self.current['value'] = node.value
        self.setbase(node)

    def visit_BooleanNode(self, node: mparser.BooleanNode) -> None:
        self.gen_ElementaryNode(node)

    def visit_IdNode(self, node: mparser.IdNode) -> None:
        self.gen_ElementaryNode(node)

    def visit_NumberNode(self, node: mparser.NumberNode) -> None:
        self.gen_ElementaryNode(node)

    def visit_StringNode(self, node: mparser.StringNode) -> None:
        self.gen_ElementaryNode(node)

    def visit_FormatStringNode(self, node: mparser.FormatStringNode) -> None:
        self.gen_ElementaryNode(node)

    def visit_ArrayNode(self, node: mparser.ArrayNode) -> None:
        self._accept('args', node.args)
        self.setbase(node)

    def visit_DictNode(self, node: mparser.DictNode) -> None:
        self._accept('args', node.args)
        self.setbase(node)

    def visit_OrNode(self, node: mparser.OrNode) -> None:
        self._accept('left', node.left)
        self._accept('right', node.right)
        self.setbase(node)

    def visit_AndNode(self, node: mparser.AndNode) -> None:
        self._accept('left', node.left)
        self._accept('right', node.right)
        self.setbase(node)

    def visit_ComparisonNode(self, node: mparser.ComparisonNode) -> None:
        self._accept('left', node.left)
        self._accept('right', node.right)
        self.current['ctype'] = node.ctype
        self.setbase(node)

    def visit_ArithmeticNode(self, node: mparser.ArithmeticNode) -> None:
        self._accept('left', node.left)
        self._accept('right', node.right)
        self.current['op'] = arithmic_map[node.operation]
        self.setbase(node)

    def visit_NotNode(self, node: mparser.NotNode) -> None:
        self._accept('right', node.value)
        self.setbase(node)

    def visit_CodeBlockNode(self, node: mparser.CodeBlockNode) -> None:
        self._accept_list('lines', node.lines)
        self.setbase(node)

    def visit_IndexNode(self, node: mparser.IndexNode) -> None:
        self._accept('object', node.iobject)
        self._accept('index', node.index)
        self.setbase(node)

    def visit_MethodNode(self, node: mparser.MethodNode) -> None:
        self._accept('object', node.source_object)
        self._accept('args', node.args)
        self.current['name'] = node.name.value
        self.setbase(node)

    def visit_FunctionNode(self, node: mparser.FunctionNode) -> None:
        self._accept('args', node.args)
        self.current['name'] = node.func_name.value
        self.setbase(node)

    def visit_AssignmentNode(self, node: mparser.AssignmentNode) -> None:
        self._accept('value', node.value)
        self.current['var_name'] = node.var_name.value
        self.setbase(node)

    def visit_PlusAssignmentNode(self, node: mparser.PlusAssignmentNode) -> None:
        self._accept('value', node.value)
        self.current['var_name'] = node.var_name.value
        self.setbase(node)

    def visit_ForeachClauseNode(self, node: mparser.ForeachClauseNode) -> None:
        self._accept('items', node.items)
        self._accept('block', node.block)
        self.current['varnames'] = [varname.value for varname in node.varnames]
        self.setbase(node)

    def visit_IfClauseNode(self, node: mparser.IfClauseNode) -> None:
        self._accept_list('ifs', node.ifs)
        self._accept('else', node.elseblock)
        self.setbase(node)

    def visit_UMinusNode(self, node: mparser.UMinusNode) -> None:
        self._accept('right', node.value)
        self.setbase(node)

    def visit_IfNode(self, node: mparser.IfNode) -> None:
        self._accept('condition', node.condition)
        self._accept('block', node.block)
        self.setbase(node)

    def visit_TernaryNode(self, node: mparser.TernaryNode) -> None:
        self._accept('condition', node.condition)
        self._accept('true', node.trueblock)
        self._accept('false', node.falseblock)
        self.setbase(node)

    def visit_ArgumentNode(self, node: mparser.ArgumentNode) -> None:
        self._accept_list('positional', node.arguments)
        kwargs_list: T.List[T.Dict[str, T.Dict[str, T.Any]]] = []
        for key, val in node.kwargs.items():
            key_res: T.Dict[str, T.Any] = {}
            val_res: T.Dict[str, T.Any] = {}
            self._raw_accept(key, key_res)
            self._raw_accept(val, val_res)
            kwargs_list += [{'key': key_res, 'val': val_res}]
        self.current['kwargs'] = kwargs_list
        self.setbase(node)
