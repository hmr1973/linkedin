import os
import json
import random
import requests
import feedparser
import html
import time

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv


# =====================================================
# CONFIGURAÇÃO
# =====================================================

load_dotenv()

BUFFER_API_KEY = os.getenv("BUFFER_API_KEY")
CHANNEL_ID = os.getenv("BUFFER_CHANNEL_ID")

RSS_URL = os.getenv(
    "RSS_URL",
    "https://sucesso.hmr1973.com/feed/"
)

BUFFER_URL = "https://api.buffer.com"

QTD_POSTS = 10


# =====================================================
# VALIDAR
# =====================================================

if not BUFFER_API_KEY:
    raise Exception("BUFFER_API_KEY não informado")

if not CHANNEL_ID:
    raise Exception("BUFFER_CHANNEL_ID não informado")


# =====================================================
# LER RSS COMPLETO
# =====================================================

def ler_rss():
    print("\nLendo RSS...")

    feed = feedparser.parse(RSS_URL)

    artigos = []

    for item in feed.entries:
        titulo = item.get("title", "")
        link = item.get("link", "")

        resumo = item.get(
            "summary",
            item.get("description", "")
        )

        resumo = html.unescape(resumo)

        artigos.append({
            "title": titulo.strip(),
            "link": link.strip(),
            "contentSnippet": resumo.strip()
        })

    print(f"Feeds encontrados: {len(artigos)}")

    return artigos


# =====================================================
# ESCOLHER ALEATÓRIOS
# =====================================================

def escolher_posts(artigos):
    quantidade = min(QTD_POSTS, len(artigos))

    return random.sample(
        artigos,
        quantidade
    )


# =====================================================
# TEXTO LINKEDIN
# =====================================================

def criar_post(artigo):
    texto = f"""
{artigo['title']}

{artigo['contentSnippet'][:500]}

Leia mais:
{artigo['link']}

#digitalmarketing #instagram #startup #branding #instagood #mindset #finance #investment #design #inspiration #socialmedia #fashion #lifestyle #realestate #technology #work #businesswoman #socialmediamarketing #goals #life
"""

    return texto.strip()


# =====================================================
# BUFFER GRAPHQL: POST SOMENTE TEXTO
# =====================================================

def publicar_buffer(texto):
    horario = (
        datetime.now(timezone.utc)
        + timedelta(minutes=5)
    ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
        createPost(input: $input) {
            ... on PostActionSuccess {
                post {
                    id
                    text
                    dueAt
                }
            }

            ... on MutationError {
                message
            }
        }
    }
    """

    variables = {
        "input": {
            "text": texto,
            "channelId": CHANNEL_ID,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": horario
        }
    }

    resposta = requests.post(
        BUFFER_URL,
        headers={
            "Authorization": f"Bearer {BUFFER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "query": mutation,
            "variables": variables
        },
        timeout=30
    )

    resposta.raise_for_status()

    return resposta.json()


# =====================================================
# EXECUÇÃO
# =====================================================

def main():
    artigos = ler_rss()

    if not artigos:
        print("RSS vazio")
        return

    posts = escolher_posts(artigos)

    print(f"\nSerão agendados {len(posts)} posts")

    for indice, artigo in enumerate(posts, start=1):
        print("\n================================")
        print(f"Publicação {indice}/{len(posts)}")
        print(artigo["title"])

        texto = criar_post(artigo)

        try:
            resultado = publicar_buffer(texto)

            print("\nResposta Buffer:")
            print(
                json.dumps(
                    resultado,
                    indent=4,
                    ensure_ascii=False
                )
            )

        except requests.RequestException as erro:
            print(f"\nErro de comunicação com o Buffer: {erro}")

        except ValueError as erro:
            print(f"\nResposta inválida do Buffer: {erro}")

        # Evita disparos simultâneos; não espera após o último post.
        if indice < len(posts):
            time.sleep(10)


if __name__ == "__main__":
    main()