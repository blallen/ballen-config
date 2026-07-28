# Engineering defaults

Repository instructions and executable configuration take precedence.

Use staff-level judgment and choose the simplest sufficient solution. Optimize
for readability and maintainability. Avoid unrelated scope, and run fresh
verification before claiming completion.

For Python repositories unless their own configuration says otherwise:

- Use Python 3.12.
- Use type hints, `TypedDict` for controlled mapping shapes, and Pydantic v2 for
  validated models.
- Use Google-style docstrings and pytest fixtures.

Use Jujutsu when `.jj/` is present; otherwise use the repository's selected
source-control system.

Write responses without emojis, and keep the tone friendly and technically
focused.
