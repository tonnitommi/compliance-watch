# Export Compliance Watch (demo)

Watches new rules in US Federal BIS export compliance site (things like sanctions list entries), and creates a agent threads out of them for further chatting.

🎥 Check out a [video](https://www.youtube.com/watch?v=2IX1XiZ9uRA) of the Agent in action! 🎥

- Setup [OpenGPTs](https://github.com/langchain-ai/opengpts).
- Setup [Sema4.ai Action Server](https://github.com/Sema4AI/actions) and run with actions found [here](/actions).
- Create a bot (assistant) with attached [prompts](prompts.txt), connect the Actions Server and remember to create use the [empty file](empty.txt) for RAG retriever as otherwise the retrievel tool is not added.
- Change the assistant id and your user id to the code around [here](https://github.com/tonnitommi/compliance-watch/blob/6a8f927d86e37c23ac4fe097f419c3df23add709/tasks/tasks.py#L135).
- Make sure you have all Robocorp Control Room things running (the task uses Vault).
- Run the task, it watches for the site updates, creates threads to Agent and sends emails (remember to change your own email in the code ;)
