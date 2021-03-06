from tokens import *
from ast import *

###############################################################################
#                                                                             #
#  PARSER                                                                     #
#                                                                             #
###############################################################################

class Parser(object):
    def __init__(self, lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()
        self.next_token = self.lexer.get_next_token()
    def error(self,token_type=None):
        raise Exception("Expected %s Token at pos %s, got %s" % \
            (token_type, self.lexer.pos, self.current_token))
    def eat(self, token_type):
        #print self.current_token, self.next_token
        if self.current_token.type == token_type:
            self.current_token = self.next_token
            self.next_token = self.lexer.get_next_token()
        else:
            self.error(token_type)
    def program(self):
        if self.current_token.type == BEGIN:
            return self.begin_block()
        elif self.current_token.type in [SELECT, DEFUN]:
            return self.statement()
        else:
            return self.expr()
    def begin_block(self):
            self.eat(BEGIN)
            statements = []
            while self.current_token.type != END:
                statements.append(self.program())
                self.eat(SEMI)
            self.eat(END)
            return UnOp(Token(BEGIN, BEGIN), Token(LIST, statements))
    def statement(self):
        if self.current_token.type == SELECT:
            return self.select_statement()
        else: #if self.current_token.type == DEFUN:
            return self.def_func()
    def select_statement(self):
        self.eat(SELECT)
        columns = self.cols()
        self.eat(FROM)
        db = self.db()
        if self.current_token.type == WHERE:
            self.eat(WHERE)
            cond = self.expr()
        else:
            cond = None
        return TriOp(Token(SELECT, SELECT), columns, db, cond)
    def cols(self):
        if self.current_token.value == "*":
            self.eat(OP)
            return "*"
        else:
            columns = []
            columns.append(self.expr())
            while self.current_token.type == COMMA:
                self.eat(COMMA)
                columns.append(self.expr()) 
            return columns
    def db(self):
        token = self.current_token
        self.eat(ID)
        return DB(token)
    def def_func(self):
        self.eat(DEFUN)
        name = Var(self.current_token)
        self.eat(ID)
        self.eat(COLON)
        params = []
        if self.current_token.type != ARROW:
            params.append(Var(self.current_token))
            self.eat(ID)
        while self.current_token.type != ARROW:
            self.eat(COMMA)
            params.append(Var(self.current_token))
            self.eat(ID)
        self.eat(ARROW)
        body = self.program()
        return FuncDecl(name, params, body)
    def expr(self):
        if self.current_token.type == BEGIN:
            return self.begin_block()
        elif self.next_token.value in [":=", "||=", "*=", "+=", "-="]:
            return self.asgn()
        else:
            curr = self.fact0()
            if self.current_token.value == "?":
                self.eat(QMARK)
                first = self.expr()
                self.eat(COLON)
                second = self.expr()
                return TriOp(Token(OP, "?:"), curr, first, second)
            else:
                return curr    
    def fact0(self):
        curr = self.fact1()
        while self.current_token.value in ["&", "|"]:
            op = self.current_token
            self.eat(OP)
            curr = BinOp(op, curr, self.fact1())
        return curr 
    def fact1(self):
        curr = self.fact2()
        while self.current_token.value in ["=", "<>"]:
            op = self.current_token
            self.eat(OP)
            curr = BinOp(op, curr, self.fact2())
        return curr 
    def fact2(self):
        curr = self.fact3()
        while self.current_token.value in ["<", ">"]:
            op = self.current_token
            self.eat(OP)
            curr = BinOp(op, curr, self.fact3())
        return curr 
    def fact3(self):
        curr = self.fact4()
        while self.current_token.value in ["+", "-", "||"]:
            op = self.current_token
            self.eat(OP)
            curr = BinOp(op, curr, self.fact4())
        return curr 
    def fact4(self):
        curr = self.const()
        while self.current_token.value in ["*"]:
            op = self.current_token
            self.eat(OP)
            curr = BinOp(op, curr, self.const())
        return curr 
    def const(self):
        if self.current_token.type == OP and self.current_token.value in ["-", "+", "!"]:
            op = self.current_token
            self.eat(OP)
            return UnOp(op, self.const()) 
        if self.current_token.type == LPAREN:
            self.eat(LPAREN)
            expr = self.expr()
            self.eat(RPAREN)
            return expr
        elif self.next_token.type == LPAREN:
            return self.func_call()
        elif self.current_token.type == ID:
            var = self.current_token
            self.eat(ID)
            return Var(var)
        elif self.current_token.type == STR:
            string = self.current_token
            self.eat(STR)
            return String(string)
        elif self.current_token.type == INT:
            integer = self.current_token
            self.eat(INT)
            return Integer(integer)
        elif self.current_token.type == BOOL:
            boolean = self.current_token
            self.eat(BOOL)
            return Boolean(boolean)
    def asgn(self):
        var = Var(self.current_token)
        self.eat(ID)
        if self.current_token.value == ":=":
            self.eat(OP)
            val = self.expr()
            return Assign(var, val)
        elif self.current_token.value == "||=":
            self.eat(OP)
            val = self.expr()
            return Assign(var, BinOp(Token(OP, "||"), var, val))
        elif self.current_token.value == "*=":
            self.eat(OP)
            val = self.expr()
            return Assign(var, BinOp(Token(OP, "*"), var, val))
        elif self.current_token.value == "+=":
            self.eat(OP)
            val = self.expr()
            return Assign(var, BinOp(Token(OP, "+"), var, val))
        else: 
            self.error() #TODO: add support for ||=   
    def func_call(self):
        name = self.current_token
        self.eat(ID)
        self.eat(LPAREN)
        params = []
        while self.current_token.type != RPAREN:
            params.append(self.expr())
            if self.current_token.type != COMMA:
                break
            else:
                self.eat(COMMA)
        self.eat(RPAREN)
        return FuncCall(name, params)   
    def echo(self):
        self.eat(ECHO)
        return UnOp(Token(ECHO, ECHO), self.val())
    def parse(self):
        while self.current_token.type != EOF:
            result = self.program()
            if self.current_token.type == SEMI:
                self.eat(SEMI)
            elif self.current_token.type != EOF:
                self.error(EOF)
        return result
