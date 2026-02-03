# Shalev

**A framework for systematic document editing using LLMs.**

![A mechanical arm](img/shalev_illustration.png)

Shalev is a framework for integrating LLMs in the process of writing books, extensive research papers, theses, or book-like websites. The general idea is that structure, ideas, and style are laid out by the (human) **authors**, while LLM-agents help refine content and synchronize style and content among various parts of the book. Shalev is particularly geared towards books of a _scientific_, _mathematical_, or _programming_ nature, but it is not limited to these types of creations.

At the moment Shalev, under development, is a CLI tool and a conceptual framework for book editing. In the future Shalev may be a visual studio code (or other IDE) plug-in, but there are no plans for this yet. In any case, the Shalev framework heavily relies on git workflows, as any changes to a component are committed, together with metadata. Also in any Shalev project, it is typical that the authors program, or "prompt engineer", from time to time, as part of their book writing process. These  auxillary programs, or LLM prompts, are also stored as part of the project and are used to help create and improve the project.

Shalev has two main components, **Shalev Agent Framework** (SAF) and **Shalev Composer Framework** (SCF). The SAF is the part associated with carrying out LLM/AI agent based tasks on components. The SCF is simply the tool that aggregates the components into a document that is compiled via LaTeX, pandoc, or other means. A Shalev **project** (book) has metadata associated both with the SAF and SCF, and this metadata, also edited during the book writing processes, specifies for the SAF and the SCF how to carry out various **actions**. Some metadata has to do with the whole project, either for the SAF or SCF, while other metadata is component specific.

Both the SAF and SCF have associated **actions** and the main use of the Shalev CLI is to execute these actions. SAF actions carry out LLM-Agent computations to transform components. This can include rewriting a component, uniformizing the style of several components, and other custom LLM-Agent based actions applied to the body of the project. SCF actions are more straightforward and include compilation of the components into the **latest draft** and similar formatting actions using LaTeX, pandoc, etc.

Note also that an important part of Shalev has to do with **review feedback** and its implementation in the project. In such cases, metadata of components includes annotated (human) review feedback from proofreading and revising. Then SAF actions can implement this feedback either locally or across many or all components.

Also note that some SAF actions do not change the actual body of a component but rather check for consistency, comparison of example code (in case the book has computer programming code) output, and similar checks.

## Components and the basic action of SCF

The atoms of a Shalev project are called **components** where you can think of a component as a part of the book. Each component has a **component type** where component types can be _chapter_, _section_, _subsection_, _code-snippet_, etc. Shalev comes with basic component types motivated by the example projects it was developed for. New component types can be defined as well. Depending on the component type, some components can have children (e.g. a _chapter_ can have _sections_ as children). These component types are **non-leaf** components. Other  component types are **leafs** (e.g. a _code-snippet_). There is also the **root** component which is the whole project and it includes all other components.

In Git, components reside in the `components` folder, where each subfolder of `components` is a uniquely named component. E.g. `diffusion_example_a`. Now the component directory, `diffusion_example_a` has one textual (LaTeX, Markdown, TikZ, etc, plain text...) file that is called `body.txt` and another file called `metadata.json`. A full specification of the metadata is in the sequel. As for the body, it is pure text, or code (in case the project includes computer code), but for non-leaf components it can also have lines such as

```
!!!>include(foo)
```

where `foo` is a different component name. Note also that one component is called `root`.

All components are included via a tree structure from `root`, and (typically) every component is included only once.

This structure then allows the main action of the SCF, **compose** to execute. The basics of this action is to construct all of the components into one source file, e.g. a valid complete LaTeX file, and then produce output via LaTeX compilation. Via the CLI this is just executed as,

```
shalev compose <project>
```

where `<project>` is the name of the project as defined in your workspace configuration. The project argument is optional: if the workspace has a single project it is auto-selected, and if a default project is set via `shalev default-project` it is used.

Note that while some actions come with the Shalev CLI, most actions are project specific. YAML specification for all actions is stored in the `actions` folder which has the `SCF` and `SAF` subfolders. So for example for `compile`, there is the `compile.py` file inside `actions/SCF` and this script would first use another action which comes with the Shalev Python package, `composeproject`, and then execute LaTeX (pandoc or similar) on the intermediate composed project (where all sub components were included). Note that there is also a `tmp` folder where intermediate files are stored.

## Actions of the SAF

SAF actions are what makes Shalev useful and effective. These actions apply LLM-Agents on components to iterate them and improve them. Many mundane editing tasks are automated via SAF actions. An action modifies a single component, where sometimes the `body.txt` file is modified and sometimes the `metadata.json` file is modified, and sometimes both.

SAF actions are stored in the `actions/SAF` folder. Here are a few actions, **general_proofread**, **transform_code**, **apply_comments**, and a few more.

The specification of these actions and how they related different components is the core part of Shalev and is still being developed. In a nutshell, Shalev runs an LLM to use these actions.

For example,

```
shalev agent general_proofread myproject~root
```

applies a general proofread to the `root` component in `myproject`. Proofreading content is then recorded in the metadata file of the component.

Or,

```
shalev agent transform_julia_to_python myproject~example_normal_dist_julia myproject~example_normal_dist_python
```

applies a specific action called `transform_julia_to_python` which translates Julia code to Python code. It takes the component `example_normal_dist_julia` as the source and `example_normal_dist_python` as the destination component. Note the `project~component` format where the project name and component name are separated by a tilde (`~`). If a default project is set (via `shalev default-project`), you can omit the project prefix and just write the component name.

There are many more useful actions, some of which come with Shalev and others can be customized in the project.

## The Shalev Config

A Shalev project has the `config` folder which has files that specify certain settings such the LLM to use a (.gitignored) file that has API keys, and other content.

## Installation

See Developer install below.

## Shalev CLI Commands

The two main commands used during a document editing workflow are:

```
shalev compose [<project>]                            # Compose components into a document
shalev agent <action> <project~component>...          # Run LLM agent actions (component without ~ uses default project)
```

All available commands:

```
shalev setup -p <handle> [-p <handle2> ...] [<dir>]  # Set up a new workspace
shalev compose [<project>] [--show-log]               # Compose components into a document
shalev view [<project>]                               # Open the composed PDF
shalev tree [<project>]                               # Display the component include tree
shalev agent <action> <project~component>...          # Run LLM agent actions (component without ~ uses default project)
shalev agent --list                                   # List all available actions
shalev agent <action> <project~folder> --all <ext>    # Run action on all files with given extension in folder
shalev split <component> --split-type <cmd>           # Split a component at LaTeX commands into sub-components
shalev split <component> --split-type <cmd> --target <dir> --numbered [<prefix>]
shalev flush [<project>]                                # Delete all files in the build folder
shalev default-project [<handle>]                     # View or set the default project
shalev config [-w <workspace>]                        # View or set workspace configuration
shalev status                                         # Display workspace status
shalev alias <short_name> <project~component>         # Create a component alias
shalev alias --list                                   # List all aliases
```

Most commands accept `--show-shalev-log` to display internal log messages. The `compose` command also accepts `--show-log` to display the full LaTeX compilation output.

## Developer install

### Prerequisites

Only tested on macOS at this stage.

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- pdflatex (install via [MacTeX](https://www.tug.org/mactex/) or `brew install --cask mactex`)
- An [OpenAI API key](https://platform.openai.com/api-keys) — Shalev currently uses OpenAI for its LLM operations. Set it in your shell before running Shalev:

  ```
  export OPENAI_API_KEY=<your-key>
  ```

  Store the key securely (e.g. in your shell profile or a secrets manager) and avoid committing it to version control.

### Install

```
git clone git@github.com:Shalev-AI/shalev.git
cd shalev
uv tool install --editable .
```

This installs `shalev` as a CLI command available globally. The `--editable` flag means any changes you make to the source files take effect on the next run without reinstalling.

### Example workspace

An example LaTeX workspace is available at [Shalev-AI/example-latex-workspace](https://github.com/Shalev-AI/example-latex-workspace). Clone it to try out Shalev:

```
git clone git@github.com:Shalev-AI/example-latex-workspace.git
```

Then point Shalev at it:

```
shalev config -w <path-to-example-latex-workspace>
```

Verify the installation:

```
shalev status
```

You should see your `workspace_config.yaml` file.

### Uninstall

```
uv tool uninstall shalev
```

## Motivation

At the moment, Shalev is being developed to aid the creation of the following books (or some subset):

* _Linear Algebra with Julia and JAX: Fundamentals for Data Science, Machine Learning and Artificial Intelligence_: This book will be based on short Julia and JAX (Python) code examples. Linear algebra concepts will be augmented with both Julia and JAX examples. Among other tasks, Shalev will be used to ensure consistency among examples and across the two languages (Julia and JAX/Python).
* _Statistics with Julia: Fundamentals for Data Science, Machine Learning and Artificial Intelligence, Second Edition._ The [first edition](https://statisticswithjulia.org/) will be revised with agent framework actions.
* _Statistics with Python: Fundamentals for Data Science, Machine Learning and Artificial Intelligence._ This is a port of Statistics with Julia, adapted to Python. Shalev will be used for the port.
* _The Tales of Curious Epsilon_. This book is an exploratory mathematics book based on old existing blog posts. The writing style is very different to the other books.
* _Structured Markov Chains and Linear Control Theory_. An early [rough version](https://people.smp.uq.edu.au/YoniNazarathy/AMSIschool2016/bookSS16_WHOLE_BOOK_v2.pdf) of this book exists and Shalev will be used to as an aid to complete it.
* _Twenty Methods in Data Science and the Mathematics Behind Them_. This book does not exist but was conceptualized a few years ago. It is a book the presents an exposition of why maths is useful for data science.
* _The Mathematical Engineering of Deep Learning, Second edition_. The [first edition](https://deeplearningmath.org/) exists but deep learning is moving very fast and there is room to update to a second edition, also with the help of Shalev.

The need and opportunity for a tool like Shalev became apparent during work on [_The Mathematical Engineering of Deep Learning_](https://deeplearningmath.org/) especially since Chat-GPT became available during the final year of work on that book. Yet for that book, using Chat-GPT for anything beyond table and formula formatting was not really possible as the style and messaging of the book needed to be kept and any Chat-GPT text generated was not really useful. Still, working on a deep learning book during the Chat-GPT era made it clear that many editing tasks can be automated in ways where the authors have (almost) full control of the final product, and where LLMs save an immense amount of time. Note that many of these tasks are not directly related to English language or creative writing, but are rather related to tasks of enforcing style and consistency along the book among others.

Shalev is also related to the world of automatic software creation (e.g. GitHub co-pilot). A general paradigm that it attempts to employ is [flow engineering](https://arxiv.org/abs/2401.08500).

We note that Shalev can help with creation and editing of freeform text, mathematical formulas, bibliography, computer programming code (appearing in book), [TikZ](https://texample.net/tikz/examples/) illustrations and other elements appearing the book.

## About the name

The name is motivated by the late author, [Meir Shalev](https://en.wikipedia.org/wiki/Meir_Shalev) as well as the similar Hebrew word "shiluv" (שילוב) which means "combination". Indeed as attested by Meir Shalev, he used to write his novels based on various sub-components which he would later combine into a cohesive story. Similarly, in Shalev, the basic entity is a **component** (typically a piece of text) which is combined into the final product. Importantly, in Shalev, the components are manipulated and refined with the help of LLM along the way. LLM-Agents are used to improve text, implement comments, uniformize style, and test for consistency, among other tasks.