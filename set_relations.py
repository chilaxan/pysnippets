def is_reflexive(A, R):
	for a in A:
		if (a, a) not in R:
			return False
	return True

def is_symetric(A, R):
	for a in A:
		for b in A:
			if (a, b) in R:
				if (b, a) not in R:
					return False
	return True

def is_transitive(A, R):
	for a in A:
		for b in A:
			for c in A:
				if (a, b) in R and (b, c) in R:
					if not (a, c) in R:
						return False
	return True

## syntax
E == E # R, S, T
E > E # T
E < E # T
E >= E # R, S, T
E <= E # R, S, T

# need a way to specify if propery is transitive
E ? E # non-transitive property # R, S

{(a, b): a ? b}
{(a, b): a is friends with b}
{(a, b): (a.age == b.age) || (a.height > b.height)}
