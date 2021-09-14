#define NS_BEGIN(name) __import__("builtins").__ns_globals__ = globals().copy(); globals().clear(); __ns_name__ = #name ;
#define NS_END __ns__=__import__("types").SimpleNamespace(**{k: v for k, v in globals().items() if k != "__ns_name__"}); __import__("builtins").__ns_globals__[__ns_name__]=__ns__; globals().clear(); globals().update(__import__("builtins").__ns_globals__)
