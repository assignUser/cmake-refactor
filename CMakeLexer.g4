lexer grammar CMakeLexer;
options 
{
  language=Python3;
  caseInsensitive = true;
}

channels {
  WHITESPACE,
  COMMENTS
}


Add_command
	: 'add_library' | 'add_executable'
	;

Target_command
	: 'target_'[a-z0-9_]+
	;

Lparen
	: '('	
	;

Rparen
	: ')' 	
	;

Identifier
	: [a-z_][a-z0-9_]*
	;

Unquoted_argument
	: (~[ \t\r\n()#"\\] | Escape_sequence)+
	;

Escape_sequence
	: Escape_identity | Escape_encoded | Escape_semicolon
	;

fragment
Escape_identity
	: '\\' ~[a-z0-9;]
	;

fragment
Escape_encoded
	: '\\t' | '\\r' | '\\n'
	;

fragment
Escape_semicolon
	: '\\;'
	;

Quoted_argument
	: '"' (~[\\"] | Escape_sequence | Quoted_cont)* '"'
	;

fragment
Quoted_cont
	: '\\' ('\r' '\n'? | '\n')
	;

Bracket_argument
	: '[' Bracket_arg_nested ']'
	;

fragment
Bracket_arg_nested
	: '=' Bracket_arg_nested '='
	| '[' .*? ']'
	;

Bracket_comment
	: '#[' Bracket_arg_nested ']'
	-> channel(COMMENTS)
	;

Line_comment
	: '#' (  // #
	  	  | '[' '='*   // #[==
		  | '[' '='* ~('=' | '[' | '\r' | '\n') ~('\r' | '\n')*  // #[==xx
		  | ~('[' | '\r' | '\n') ~('\r' | '\n')*  // #xx
		  ) ('\r' '\n'? | '\n' | EOF)
    -> channel(COMMENTS)
	;

Newline
	: ('\r' '\n'? | '\n')+
	-> channel(WHITESPACE)
	;

Space
	: [ \t]+
	-> channel(WHITESPACE)
	;
