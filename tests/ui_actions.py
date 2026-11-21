"""Gesto explícito adicional nos testes dos formulários protegidos."""
def confirm_action(app):
    assert not app.exception
    return app.button(key='action_confirm').click().run()
