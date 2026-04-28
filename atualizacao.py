# atualizacao.py
from flask import jsonify, request
from main import app
from db import conexao
from funcao import decodificar_token
import os
from datetime import datetime


# ============================================
# ROTA: Feed de atualizações (público)
# ============================================
@app.route('/feed_atualizacoes', methods=['GET'])
def feed_atualizacoes():
    """Feed público de atualizações com filtro de ordem"""
    filtro = request.args.get('filtro', 'recentes')

    con = conexao()
    cur = con.cursor()

    try:
        # Define a ordem baseado no filtro
        if filtro == 'antigos':
            ordem = 'ASC'
        else:
            ordem = 'DESC'  # recentes (padrão)

        cur.execute(f"""
            SELECT a.ID_ATUALIZACOES, a.ID_PROJETOS, a.TITULO, a.TEXTO, a.DATA_CRIACAO,
                   p.ID_USUARIOS, p.TITULO, u.NOME
            FROM ATUALIZACOES a
            LEFT JOIN PROJETOS p ON a.ID_PROJETOS = p.ID_PROJETOS
            LEFT JOIN USUARIOS u ON p.ID_USUARIOS = u.ID_USUARIOS
            ORDER BY a.DATA_CRIACAO {ordem}
        """)

        dados = cur.fetchall()
        print(f"DEBUG - Feed total: {len(dados) if dados else 0} | Ordem: {ordem}")

        lista = []
        if dados:
            for a in dados:
                data_str = ''
                if a[4]:
                    try:
                        data_str = a[4].strftime('%d/%m/%Y %H:%M')
                    except:
                        data_str = str(a[4])

                lista.append({
                    'id': a[0],
                    'projeto_id': a[1],
                    'titulo': str(a[2]) if a[2] else '',
                    'texto': str(a[3]) if a[3] else '',
                    'data': data_str,
                    'ong_id': a[5] if a[5] else 0,
                    'projeto_titulo': str(a[6]) if a[6] else '',
                    'ong_nome': str(a[7]) if a[7] else 'ONG',
                    'ong_foto': f'{a[5]}.jpeg' if a[5] else 'ong-icon.png',
                    'foto': f'{a[0]}.jpeg'
                })

        return jsonify({'atualizacoes': lista}), 200
    except Exception as e:
        print(f"ERRO feed_atualizacoes: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Listar atualizações da ONG logada
# ============================================
@app.route('/listar_atualizacoes', methods=['GET'])
def listar_atualizacoes_ong():
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401

    id_usuarios = token_data['id_usuarios']
    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT a.ID_ATUALIZACOES, a.ID_PROJETOS, a.TITULO, a.TEXTO, a.DATA_CRIACAO
            FROM ATUALIZACOES a
            INNER JOIN PROJETOS p ON a.ID_PROJETOS = p.ID_PROJETOS
            WHERE p.ID_USUARIOS = ?
            ORDER BY a.DATA_CRIACAO DESC
        """, (id_usuarios,))

        atualizacoes = cur.fetchall()

        lista_atualizacoes = []
        for a in atualizacoes:
            data_str = ''
            if a[4]:
                try:
                    data_str = a[4].strftime('%d/%m/%Y %H:%M')
                except:
                    data_str = str(a[4])

            lista_atualizacoes.append({
                'id': a[0],
                'projeto_id': a[1],
                'titulo': str(a[2]) if a[2] else '',
                'texto': str(a[3]) if a[3] else '',
                'data': data_str,
                'foto': f'{a[0]}.jpeg'
            })

        return jsonify({'atualizacoes': lista_atualizacoes}), 200
    except Exception as e:
        print(f"ERRO listar_atualizacoes: {e}")
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Criar atualização
# ============================================
@app.route('/criar_atualizacao', methods=['POST'])
def criar_atualizacao():
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401
    if token_data['tipo'] != 2:
        return jsonify({'error': 'Apenas ONGs podem criar atualizações'}), 403

    titulo = request.form.get('titulo', '')
    texto = request.form.get('texto', '')
    projeto_id = request.form.get('projeto_id', '')
    foto_atualizacao = request.files.get('foto')

    if not titulo.strip():
        return jsonify({"error": "Título é obrigatório"}), 400
    if not projeto_id:
        return jsonify({"error": "Projeto é obrigatório"}), 400

    con = conexao()
    cur = con.cursor()

    try:
        # Verifica se o projeto existe e pertence à ONG
        cur.execute("SELECT ID_USUARIOS FROM PROJETOS WHERE ID_PROJETOS = ?", (projeto_id,))
        projeto = cur.fetchone()
        if not projeto:
            return jsonify({"error": "Projeto não encontrado"}), 404

        if token_data['id_usuarios'] != projeto[0] and token_data['tipo'] != 0:
            return jsonify({'error': 'Sem permissão para este projeto'}), 403

        data_atual = datetime.now()

        # Gera o próximo ID manualmente
        cur.execute("SELECT GEN_ID(GEN_ATUALIZACOES, 1) FROM RDB$DATABASE")
        next_id = cur.fetchone()[0]

        # Insere com o ID gerado
        cur.execute("""INSERT INTO ATUALIZACOES (ID_ATUALIZACOES, ID_PROJETOS, TITULO, TEXTO, DATA_CRIACAO)
                       VALUES (?, ?, ?, ?, ?)""",
                    (next_id, projeto_id, titulo, texto, data_atual))

        con.commit()
        id_atualizacoes = next_id

        # Salva foto se enviada
        if foto_atualizacao:
            try:
                nome_imagem = f'{id_atualizacoes}.jpeg'
                caminho_destino = os.path.join(app.config['UPLOAD_FOLDER'], 'Atualizacoes')
                os.makedirs(caminho_destino, exist_ok=True)
                foto_atualizacao.save(os.path.join(caminho_destino, nome_imagem))
            except Exception as e:
                print(f"Erro ao salvar foto: {e}")

        return jsonify({'message': 'Atualização criada com sucesso!', 'id': id_atualizacoes}), 201
    except Exception as e:
        print(f"ERRO criar_atualizacao: {e}")
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Buscar atualização por ID
# ============================================
@app.route('/buscar_atualizacao/<int:id_atualizacoes>', methods=['GET'])
def buscar_atualizacao(id_atualizacoes):
    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("""SELECT ID_ATUALIZACOES, ID_PROJETOS, TITULO, TEXTO, DATA_CRIACAO
                       FROM ATUALIZACOES WHERE ID_ATUALIZACOES = ?""", (id_atualizacoes,))
        a = cur.fetchone()

        if not a:
            return jsonify({"error": "Atualização não encontrada"}), 404

        data_str = ''
        if a[4]:
            try:
                data_str = a[4].strftime('%d/%m/%Y %H:%M')
            except:
                data_str = str(a[4])

        return jsonify({'atualizacao': {
            'id': a[0],
            'projeto_id': a[1],
            'titulo': str(a[2]) if a[2] else '',
            'texto': str(a[3]) if a[3] else '',
            'data': data_str
        }}), 200
    except Exception as e:
        print(f"ERRO buscar_atualizacao: {e}")
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Editar atualização
# ============================================
@app.route('/editar_atualizacao/<int:id_atualizacoes>', methods=['PUT'])
def editar_atualizacao(id_atualizacoes):
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401

    con = conexao()
    cur = con.cursor()

    try:
        # Verifica se a atualização existe
        cur.execute("SELECT ID_PROJETOS FROM ATUALIZACOES WHERE ID_ATUALIZACOES = ?", (id_atualizacoes,))
        atualizacao = cur.fetchone()
        if not atualizacao:
            return jsonify({"error": "Atualização não encontrada"}), 404

        # Verifica se o projeto pertence à ONG
        cur.execute("SELECT ID_USUARIOS FROM PROJETOS WHERE ID_PROJETOS = ?", (atualizacao[0],))
        projeto = cur.fetchone()

        if token_data['tipo'] != 0 and token_data['id_usuarios'] != projeto[0]:
            return jsonify({'error': 'Sem permissão'}), 403

        titulo = request.form.get('titulo', '')
        texto = request.form.get('texto', '')
        projeto_id = request.form.get('projeto_id', '')
        foto_atualizacao = request.files.get('foto')

        cur.execute("""UPDATE ATUALIZACOES SET ID_PROJETOS = ?, TITULO = ?, TEXTO = ?, DATA_CRIACAO = ?
                       WHERE ID_ATUALIZACOES = ?""",
                    (projeto_id, titulo, texto, datetime.now(), id_atualizacoes))
        con.commit()

        # Salva foto se enviada
        if foto_atualizacao:
            try:
                nome_imagem = f'{id_atualizacoes}.jpeg'
                caminho_destino = os.path.join(app.config['UPLOAD_FOLDER'], 'Atualizacoes')
                os.makedirs(caminho_destino, exist_ok=True)
                foto_atualizacao.save(os.path.join(caminho_destino, nome_imagem))
            except Exception as e:
                print(f"Erro ao salvar foto: {e}")

        return jsonify({'message': 'Atualização editada com sucesso!'}), 200
    except Exception as e:
        print(f"ERRO editar_atualizacao: {e}")
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Deletar atualização
# ============================================
@app.route('/deletar_atualizacao/<int:id_atualizacoes>', methods=['DELETE'])
def deletar_atualizacao(id_atualizacoes):
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401

    con = conexao()
    cur = con.cursor()

    try:
        # Verifica se a atualização existe
        cur.execute("SELECT ID_PROJETOS FROM ATUALIZACOES WHERE ID_ATUALIZACOES = ?", (id_atualizacoes,))
        atualizacao = cur.fetchone()
        if not atualizacao:
            return jsonify({"error": "Atualização não encontrada"}), 404

        # Verifica se o projeto pertence à ONG
        cur.execute("SELECT ID_USUARIOS FROM PROJETOS WHERE ID_PROJETOS = ?", (atualizacao[0],))
        projeto = cur.fetchone()

        if token_data['tipo'] != 0 and token_data['id_usuarios'] != projeto[0]:
            return jsonify({'error': 'Sem permissão'}), 403

        cur.execute("DELETE FROM ATUALIZACOES WHERE ID_ATUALIZACOES = ?", (id_atualizacoes,))
        con.commit()

        return jsonify({'message': 'Atualização excluída com sucesso!'}), 200
    except Exception as e:
        print(f"ERRO deletar_atualizacao: {e}")
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()