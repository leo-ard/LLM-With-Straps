# LLM With Straps : An LLM Client That [Bootstraps](https://en.wikipedia.org/wiki/Bootstrapping_(compilers)) Itself

Have you ever wondered what happens if you let a Large Language Model client modify its own source code ? No need to wonder anymore with *LLM with straps*, a tiny shell utility that can modify itself to tailor it to your own specific needs. In other words, this LLM shell client can *bootstrap* itself.

## Bootstrapping ? What do you mean ?

Bootstrapping refers to the [ability for a compiler to compile itself](https://en.wikipedia.org/wiki/Bootstrapping_(compilers)). In this context, it means that this utility can fully understand its own source code and modify itself. This lets you change the utility only by using it.

## Little demo

```
$ python llm-straps.py --boot "Modify the version of chat gpt used to do requests from 4 to 3.5."
"Function 'query_model' modified successfully to use GPT-3.5."
Output written to llm-straps__1.py

$ diff llm-straps__1.py llm-straps.py
3a4
> 
145c146
< def query_model(messages, model='gpt-3.5-turbo', temperature=1, stops=[], debug=True):
---
> def query_model(messages, model='gpt-4-1106-preview', temperature=1, stops=[], debug=True):
150c151
<     model (str): Model identifier, default 'gpt-3.5-turbo'.
---
>     model (str): Model identifier, default 'gpt-4-1106-preview'.

$ cp llm-straps__1.py llm-straps.py # we now use the generated llm-straps as our main one, and it now uses chat gpt 3.5 to do requests !
```

Funny enough, this change has been incorporated in this git commit : [e37254d](https://github.com/leo-ard/LLM-With-Straps/commit/e37254dda386a63f7173e0e65a332e8a20cb1a58)

Another demo with a beep command line utility :
```
$ python llm-straps.py --boot "Add a simple command --beep in the 'main' function that prints boop to the screen"
Function 'main' modified successfully.
Output written to llm-straps__3.py

$ python llm-straps__1.py --beep test
boop

$ python llm-straps__1.py --boot "Remove the --beep command line argument in the main function"
Function 'main' modified successfully.
Output written to llm-straps__1__1.py

$ python llm-straps__1__1.py --beep test
usage: llm-straps__1__1.py [-h] [--boot] [--debug] prompt [prompt ...]
llm-straps__1__1.py: error: unrecognized arguments: --beep
```

## Setup 

To run it, you must create a virtual environment : 

```
> python3 -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt
```

Then, you must provide your open ai API key : 

```
export OPENAI_API_KEY=<your api key here>
```

And you are ready to rock ! 

```
> python llm-straps.py What is the meaning of live \?
The word "live" can have multiple meanings depending on the context. Here are a few common meanings:

1. Adjective: In the state of being alive or living, as opposed to being dead.
Example: "The live performance of the band was electric."

2. Verb: To have an active existence, to be alive, or to carry out life activities.
Example: "They live in a house by the beach."

3. Adverb: Happening or taking place in real-time, without any delay or recording.
Example: "We watched the live coverage of the football match."

4. Verb: To reside or stay and make one's home in a particular place.
Example: "Many retirees choose to live in warm climates."

5. Verb: To experience or undergo something.
Example: "She had to live through the pain of losing a loved one."

These meanings can slightly vary depending on the context and usage.
```

## History of the idea 

This idea was born in a Compiler laboratory at the University of Montreal after a great talk by Ian Arawjo. The discussion went something like this :

> Ian :
> We have decided to integrate completion tools powered by ChatGPT inside [ChainForge](https://chainforge.ai/). This is a bit circular as ChainForge is used to study LLMs and now we are using ChatGPT to complete part of the prompts used to help us analyze ChatGPT and other models.

> Marc :
> In compilation, we are used to it, it’s called bootstrapping.
