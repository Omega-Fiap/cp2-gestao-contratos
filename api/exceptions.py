class ErroAplicacao(Exception):
    """Erro de negócio ou de validação que vira resposta JSON {"erro": ...}."""

    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status
