
# tsviz

![CI](https://github.com/josteink/tsviz/workflows/CI/badge.svg)

tsviz is a command-line utility to help visualize TypeScript class-dependencies and graphs.

## features

slnviz in a nutshell:

- command-line driven.
- exports a [GraphViz](http://graphviz.org/) DOT-file from a TypeScript project directory.
- detects circular dependencies and flags them in the graph.
- highlights places where dependencies are not found in the solution.
- ability to filter redundant transistive dependencies.
- ability to exclude certain kinds of projects (test, shared, etc) from
  graph.
- ability to highlight specific projects, and dependency-paths in the graph.

## dependencies

### python

tsviz is written in Python and targets Python 3. No additional modules needs to
be installed.

It seems to work with Python 2.7 as well, but that's not a supported target.

### graphviz

If you want to visualize the graph, you need to have
[GraphViz](http://graphviz.org/) installed, or use a online service
like [viz-js](http://viz-js.com/).

## usage

The following example shows how slnviz is intended to be used:

````sh
git clone https://github.com/josteink/tsviz
cd tsviz
./tsviz.py -i ../your_repo/ -o graph.dot
dot -Tsvg -o graph.svg graph.dot
# open graph.svg in your preferred viewer
````

To list all parameters and options use the `-h` flag:

````sh
./tsviz.py -h
````
