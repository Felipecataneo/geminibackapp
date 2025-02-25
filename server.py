import asyncio
import json
import os
import websockets
from google import genai
import base64

from config import get_google_api_key

os.environ['GOOGLE_API_KEY'] = get_google_api_key()



MODEL = "gemini-2.0-flash-exp"  # use your model ID

client = genai.Client(
  http_options={
    'api_version': 'v1alpha',
  }
)

async def gemini_session_handler(client_websocket: websockets.WebSocketServerProtocol):
    """Handles the interaction with Gemini API within a websocket session."""
    try:
        config_message = await client_websocket.recv()
        config_data = json.loads(config_message)
        config = config_data.get("setup", {})
        
        config["system_instruction"] = """
Você é o assistente pessoal do Felipe, sempre pronto para ajudar com um toque de personalidade e bom humor! Seu papel é facilitar o dia a dia dele, oferecendo suporte em diversas tarefas, especialmente descrevendo o que acontece na tela ou interpretando imagens anexadas quando solicitado.

Principais diretrizes:
1. **Idioma Padrão**: O idioma principal é o português do Brasil. Sempre comunique-se de forma clara, natural e amigável.
2. **Interação Personalizada**: Conheça o Felipe pelo nome e trate-o com familiaridade, como um amigo faria. Use expressões descontraídas, mas mantenha o profissionalismo.
3. **Descrição de Telas e Imagens**: Quando Felipe compartilhar uma imagem ou pedir para descrever algo na tela, seja detalhado e objetivo. Explique o conteúdo visual de maneira acessível, destacando elementos importantes e fornecendo contexto quando relevante.
4. **Tons Positivos e Encorajadores**: Mantenha um tom positivo e encorajador em todas as interações. Seja empático e paciente, especialmente ao lidar com dúvidas ou problemas.
5. **Adaptação ao Contexto**: Esteja atento ao contexto da conversa e ajuste sua resposta conforme necessário. Seja proativo ao sugerir soluções ou ideias úteis.

Exemplo de introdução:
"Oi, Felipe! 😊 Estou aqui para te ajudar com o que precisar. Se quiser que eu descreva algo na tela ou interprete uma imagem, é só me avisar. Vamos nessa?"

Lembre-se: Você não é apenas uma ferramenta, mas também um companheiro digital que torna a vida do Felipe mais prática e divertida!
"""
        

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected to Gemini API")

            async def send_to_gemini():
                """Sends messages from the client websocket to the Gemini API."""
                try:
                  async for message in client_websocket:
                      try:
                          data = json.loads(message)
                          if "realtime_input" in data:
                              for chunk in data["realtime_input"]["media_chunks"]:
                                  if chunk["mime_type"] == "audio/pcm":
                                      #print(f"Chunk data size: {len(chunk['data'])}")
                                      #print(f"Sending audio chunk: {chunk['data'][:5]}")
                                      await session.send(input={"mime_type": "audio/pcm", "data": chunk["data"]})
                                      
                                  elif chunk["mime_type"] == "image/jpeg":
                                      print(f"Sending image chunk: {chunk['data'][:50]}")
                                      await session.send(input={"mime_type": "image/jpeg", "data": chunk["data"]})
                                      
                      except Exception as e:
                          print(f"Error sending to Gemini: {e}")
                  print("Client connection closed (send)")
                except Exception as e:
                     print(f"Error sending to Gemini: {e}")
                finally:
                   print("send_to_gemini closed")



            async def receive_from_gemini():
                """Receives responses from the Gemini API and forwards them to the client, looping until turn is complete."""
                try:
                    while True:
                        try:
                            print("receiving from gemini")
                            async for response in session.receive():
                                if response.server_content is None:
                                    print(f'Unhandled server message! - {response}')
                                    continue

                                model_turn = response.server_content.model_turn
                                if model_turn:
                                    for part in model_turn.parts:
                                        if hasattr(part, 'text') and part.text is not None:
                                            await client_websocket.send(json.dumps({"text": part.text}))
                                        elif hasattr(part, 'inline_data') and part.inline_data is not None:
                                            print("audio mime_type:", part.inline_data.mime_type)
                                            base64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                            
                                            await client_websocket.send(json.dumps({"audio": base64_audio}))
                                            
                                            print("audio received")

                                if response.server_content.turn_complete:
                                    print('\n<Turn complete>')
                                    
                        except websockets.exceptions.ConnectionClosedOK:
                            print("Client connection closed normally (receive)")
                            break  # Exit the loop if the connection is closed
                        except Exception as e:
                            print(f"Error receiving from Gemini: {e}")
                            break 

                except Exception as e:
                      print(f"Error receiving from Gemini: {e}")
                finally:
                      print("Gemini connection closed (receive)")


            # Start send loop
            send_task = asyncio.create_task(send_to_gemini())
            # Launch receive loop as a background task
            receive_task = asyncio.create_task(receive_from_gemini())
            await asyncio.gather(send_task, receive_task)


    except Exception as e:
        print(f"Error in Gemini session: {e}")
    finally:
        print("Gemini session closed.")


async def main() -> None:
    async with websockets.serve(gemini_session_handler, "0.0.0.0", 9084):
        print("Running websocket server 0.0.0.0:9084...")
        await asyncio.Future()  # Keep the server running indefinitely


if __name__ == "__main__":
    asyncio.run(main())