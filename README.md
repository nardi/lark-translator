# lark-translator

A translator addon for the [Lark](https://github.com/lark-parser/lark) parser package, inspired by the [Grammatical Framework](https://www.grammaticalframework.org).

## What this does

The idea is that, as a grammar is a structural description of a language, it can be used to both parse text and to generate text written in the language. This is already contained in the base Lark package, in the `Reconstructor` class. This object can be used to transform a parse tree back into the text which (could have) generated it.

> Of course, there are often multiple texts which lead to the same parse tree: things like whitespace are often ignored. For that reason, it may be desirable to apply some kind of formatter when reproducing the text. This is also done in the ['Reconstruct Python'](https://lark-parser.readthedocs.io/en/latest/examples/advanced/reconstruct_python.html) example in Lark's documentation.

Now how can we use this feature to achieve a kind of translation? Suppose we take a parse tree generated from text in one language, and manage to "reconstruct" a piece of text in another language, which would when parsed produce this same parse tree. If the parse tree contains all semantic information about the piece of text, we could say that since the two pieces of text produce the same parse tree, they are different expressions of the same information, and so are *translations* of each other.

The procedure, then, is simple: we take two grammars for two different languages `l1` and `l2`, and load them into Lark. We then take a piece of text written in e.g. `l1` and parse it using the `l1` grammar to obtain a parse tree `pt`. We can then "reconstruct" a text from `pt` using the `l2` grammar (under some conditions), and voila, we have the translation of the text from `l1` into `l2`. Thus, the code for the actual translation is simply this:

```python
def translate(self, text, fromlang, tolang):
    tree = parsers[fromlang].parse(text)
    return reconstructors[tolang].reconstruct(tree)

l2_text = translate(l1_text, "l1", "l2")
```

What this package contributes is two things:

1. A simple wrapper for this process.
2. A way to analyze grammars to tell whether translation between them is possible.

While this first point is quite easy, the second point is a bit more difficult. When exactly is translation between two languages possible? 

## When is translation possible?

When we wish to translate between two (formal) languages, the first condition to hold is obviously that they must be able to express the same information, only using different syntax. If this is not the case (as for all natural languages), translation becomes a fuzzy affair, and we somehow have to deal with ambiguity or loss of information. But suppose the two langauges are flexible enough that they are in principle interchangeable. For example, we could take JSON, and construct some subset of XML which basically expresses the same objects:

```json
{
    "hello": "world!"
}
```

becomes

```xml
<object>
    <property name="hello">world!</property>
</object>
```

This example is included in the `tests/grammars`-folder.

It seems reasonable to say these two examples are translations of each other. Now, there is a second question: what needs to be true of *the specific grammars* we give to Lark to parse these languages, in order for this method of translation to be applicable? In this specific case, the answer is that the two examples should parse into the same parse tree. But is there a general way to tell whether text from one language can always be translated into another?

For this, I would like to introduce the notion of *compatible grammars*. There are a couple of ways to define compatible grammars, but the core motivation is that **every parse tree obtainable from one grammar, should be an obtainable parse tree for the other grammar as well**. This is important in the case of translation, because it means that if we have the parse tree for a piece of text from one language, we can "pretend" it came from a piece of text from the other language, and then use Lark's reconstructor to obtain such a piece of text.

The definition I am currently working with is inspired by the notion of abstract syntax in the [Grammatical Framework](https://www.grammaticalframework.org). For two grammars to be compatible, a few things must be true:

1. They must contain the same named rules and terminals (i.e. same number of rules/terminals and same set of names). Aliases also count as named rules.
2. Each pair of rules with the same name must have the same *signature*. The signature of a rule specifies the possible children that a rule may have when encountered as a node in the syntax tree.
3. Each pair of terminals with the same name must match the same strings.

As you can see from this, compatible grammars must have quite a lot in common. The main place where they can differ is in the placement of *literals* between the child rules in a rule specification. This placement of literals is quite powerful, and mostly determines what the eventual text will look like.

In the implementation, it is checked whether the grammars added to a `Translator` instance are all compatible in this sense. Requirements 1 and 3 are quite easy to check, but 2 is a bit more difficult. This check is currently implemented by taking the parse tree Lark produces for the grammars themselves, and transforming it into a list of rules and their signatures. The signature of a rule consists of all possible combinations of named rules or terminals we can find as children of that rule in the parse tree. Another way to look at it is that the rule is a kind of "function" and the signature specifies all the possible arguments (= children), just like a function signature.

The arguments each rule accepts are shaped by the operations used in the grammar. `r : a | b` means the rule `r` accepts an `a` or a `b`, and similarly a rule may accept optional arguments using `?` or `[...]`, and a variable amount of arguments using `*` and `+`. All in all, any rule will accept a number of different *sequences of arguments*, things like `a b b a a`, and the specific sequences a rule accepts can be specified using a *regular expression*: not the Python kind, but the old-fashioned actually-regular kind. These regular expressions use the constructs just mentioned, and are defined over the alphabet of named rules and terminals in the grammar. As such, the signature of the rule can be represented by such a regular expression. Now, to test whether two rules are compatible, we simply generate their signatures as regular expressions, and check whether these regular expressions are equivalent (i.e. accept the same strings).

> Note that, this does not mean that the regular expressions have to be the same. There are multiple ways to write the same thing, for example `x+ x` is the same as `x x+` and the same as `x x* x`. Depending on how literals are placed, the different grammars may have to use different ways of expressing the same signature. Testing whether two regular expressions are equivalent in a more sophisticated way is therefore necessary.

This package also implements this compatibility check, so that it can guarantee that a `Translator` object will always be able to perform requested syntactic translations. However, whether the translations are also semantically correct still has to be checked by the programmer.

### Caveats

It may often be necessary when translating to transform specific strings from one thing into another. For example, if one were translating between English and German, one would like to replace all occurences of "dog" by "Hund". However, all terminals must be equivalent, so how do we accomplish this?

The way to solve this is to define the concept "dog" as a rule instead of a terminal: in the English grammar, put `word_dog: "dog"` and in the German put `word_dog: "Hund"` and the translation will be performed properly. The important distiction here is that terminals *store their contents*, while rules only keep track of their children. As such, a rule such as `word_dog` will simply be stored in the parse tree as `Rule('word_dog', [])`, while an equivalent terminal would be stored as `Token('word_dog', 'dog')` or similar. This means that the English word will be reinserted into the German text if we reconstruct the parse tree using the German grammar, despite "dog" not appearing in the grammar itself. This is a violation of compatibility, but more importantly not what we want. As such, terminals should only be used for things which are taken 'literally', in the sense that they are input from the user and so the grammar cannot account for them (e.g. a person's name, or a number), and that they can be simply copied over when performing translation.

For another example of this kind of translation, see the JSON-to-XML example, where the character `<` is treated as a special case because it opens a tag in XML and therefore must be escaped. This escaping is done by parsing `<` inside a string using a separate rule `left_bracket`, and giving this rule a different expression in the XML grammar.

### Todo list

 - Testing whether terminals are equivalent (criterion 3 for compatibility) currently doesn't happen.
 - When two grammars are incompatible, there should be helpful information provided (e.g. in which rule(s) is the incompatibility located, and how/why are they incompatible?)
 - More advanced features of Lark (such as templates) are not tested and probably don't work.
 - Some more examples/tests would be nice.
 - Also more comments and docs ;)