parser grammar CMakeParser;

options 
{
  language=Python3;
  // cmake commands are not case sensitive, only variables which are not parsed directly
  caseInsensitive = true;
  tokenVocab = CMakeLexer;
}

cmake_file: any_command* EOF;

any_command
	: add_target 
	| modify_target 
	| generic_command
	;

add_target
	: command=Add_command arguments
	;

modify_target
	: command=Target_command arguments
	;

generic_command
	: Identifier arguments
	;

arguments
	: Lparen (single_argument|compound_argument)* Rparen
	;

single_argument
	: Identifier | Unquoted_argument | Bracket_argument | Quoted_argument
	;

compound_argument
	: Lparen (single_argument|compound_argument)* Rparen
	;
