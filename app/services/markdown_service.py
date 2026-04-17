"""
Markdown Service — generates, saves, parses and updates .md files for 3Notes.AI.
Each .md is the source of truth: human-readable, ChromaDB-indexable, SQL-parseable.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

KNOWLEDGE_DIR = os.getenv("KNOWLEDGE_DIR", "./knowledge")


class MarkdownService:

    async def gerar_titulo_unico(
        self, equipamento: str, problema: str, chamado_id: int
    ) -> str:
        """Ask Gemma 4 for a concise title; prefix with CHM-YYYY-NNNN."""
        from app.services.ollama_service import ollama_service

        ano = datetime.utcnow().year
        prompt = (
            f"Gere um título conciso (máximo 8 palavras) para um chamado de manutenção hospitalar.\n"
            f"Equipamento: {equipamento}\n"
            f"Problema: {problema}\n"
            f"Formato desejado: '{equipamento} — <problema resumido em até 5 palavras>'\n"
            f"Responda APENAS com o título, sem aspas, sem explicações."
        )
        try:
            resposta = await ollama_service.completar(prompt)
            titulo_limpo = resposta.strip().strip('"').strip("'").split("\n")[0]
            if not titulo_limpo:
                titulo_limpo = f"{equipamento} — Problema reportado"
        except Exception:
            titulo_limpo = f"{equipamento} — Problema reportado"

        return f"CHM-{ano}-{chamado_id:04d} {titulo_limpo}"

    async def sugerir_tags(self, texto: str) -> list[str]:
        """Ask Gemma 4 for 5-10 kebab-case PT tags. Falls back to empty list."""
        from app.services.ollama_service import ollama_service

        prompt = (
            "Sugira de 5 a 10 tags em português para indexar este chamado de manutenção hospitalar.\n"
            "Regras: kebab-case, minúsculas, sem acentos, sem espaços.\n"
            "Exemplos: bomba-infusao, alarme, oclusao, uti, fresenius\n"
            f"Texto:\n{texto[:1000]}\n\n"
            'Responda APENAS com um array JSON de strings. Exemplo: ["tag1", "tag2", "tag3"]'
        )
        try:
            resposta = await ollama_service.completar(prompt)
            match = re.search(r"\[.*?\]", resposta, re.DOTALL)
            if match:
                tags = json.loads(match.group())
                return [t.lower().strip() for t in tags if isinstance(t, str)]
        except Exception:
            pass
        return []

    def gerar_md_chamado(
        self,
        dados: dict,
        titulo: str,
        tags: list[str],
        conversa: list[dict] | None = None,
    ) -> str:
        """Generate full .md content for a chamado (before resolution)."""
        agora = datetime.utcnow().isoformat(timespec="seconds")
        tags_yaml = json.dumps(tags, ensure_ascii=False)

        # Build conversation summary (just last user messages — not full JSON)
        conversa_texto = ""
        if conversa:
            turnos = []
            for msg in conversa:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    turnos.append(f"**Usuário:** {content}")
                elif role == "assistant" and not content.startswith("{"):
                    turnos.append(f"**Assistente:** {content}")
            conversa_texto = "\n\n".join(turnos[:10])  # max 10 turns

        md = f"""---
id: {dados.get('chamado_id', 'CHM-????')}
titulo: "{titulo}"
tags: {tags_yaml}
patrimonio: {dados.get('patrimonio', '')}
setor: {dados.get('setor', '')}
criticidade: {dados.get('criticidade_sugerida', 'medio')}
status: aberto
aberto_por: {dados.get('aberto_por', '')}
setor_reportador: {dados.get('setor_reportador', '')}
criado_em: {agora}
resolvido_em: null
---

## Problema

{dados.get('descricao_problema', '')}

## Conversa

{conversa_texto or '_Sem transcrição disponível._'}

## Tags sugeridas

{', '.join(f'`{t}`' for t in tags)}
"""
        return md

    def salvar_md(self, conteudo: str, subpasta: str, nome_arquivo: str) -> str:
        """Save .md to knowledge/{subpasta}/{nome_arquivo}.md. Returns relative path."""
        pasta = Path(KNOWLEDGE_DIR) / subpasta
        pasta.mkdir(parents=True, exist_ok=True)
        nome = nome_arquivo if nome_arquivo.endswith(".md") else f"{nome_arquivo}.md"
        caminho = pasta / nome
        caminho.write_text(conteudo, encoding="utf-8")
        return str(Path(KNOWLEDGE_DIR) / subpasta / nome)

    def atualizar_md_resolucao(
        self, md_path: str, resolucao: str, tecnico: str
    ):
        """Append ## Resolução to existing .md and update frontmatter."""
        path = Path(md_path)
        if not path.exists():
            return

        conteudo = path.read_text(encoding="utf-8")
        agora = datetime.utcnow().isoformat(timespec="seconds")

        # Update frontmatter fields
        conteudo = re.sub(r"^status: .*$", "status: resolvido", conteudo, flags=re.MULTILINE)
        conteudo = re.sub(r"^resolvido_em: .*$", f"resolvido_em: {agora}", conteudo, flags=re.MULTILINE)

        # Remove previous ## Resolução section if exists
        conteudo = re.sub(r"\n## Resolução\n[\s\S]*$", "", conteudo)

        # Append resolution
        conteudo = conteudo.rstrip() + f"\n\n## Resolução\n\n{resolucao}\n\n**Técnico responsável:** {tecnico}  \n**Resolvido em:** {agora}\n"
        path.write_text(conteudo, encoding="utf-8")

    def parse_frontmatter(self, md_path: str) -> dict:
        """Extract YAML frontmatter from a .md file."""
        try:
            conteudo = Path(md_path).read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---", conteudo, re.DOTALL)
            if not match:
                return {}
            import yaml
            return yaml.safe_load(match.group(1)) or {}
        except Exception:
            return {}

    def ler_md(self, md_path: str) -> str:
        """Return full .md content or empty string if not found."""
        try:
            return Path(md_path).read_text(encoding="utf-8")
        except Exception:
            return ""


markdown_service = MarkdownService()
