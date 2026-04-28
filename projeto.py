# projeto.py CORRIGIDO
from flask import jsonify, request
from main import app
from db import conexao
from funcao import decodificar_token
import os
from datetime import datetime


@app.route('/criar_projeto', methods=['POST'])
def criar_projeto():
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401
    if token_data['tipo'] != 2:
        return jsonify({'error': 'Apenas ONGs podem criar projetos'}), 403

    titulo = request.form.get('titulo', None)
    descricao = request.form.get('descricao', None)
    categoria = request.form.get('categoria', None)
    tipo_ajuda = request.form.get('tipo_ajuda', None)
    localizacao = request.form.get('localizacao', None)
    status = request.form.get('status', 'Ativo')
    foto_projeto = request.files.get('foto')

    id_usuarios = token_data['id_usuarios']

    con = conexao()
    cur = con.cursor()

    try:
        if not titulo or titulo.strip() == '':
            return jsonify({"error": "Título é obrigatório"}), 400
        if not descricao or descricao.strip() == '':
            return jsonify({"error": "Descrição é obrigatória"}), 400
        if not categoria:
            return jsonify({'error': 'Escolha uma categoria'}), 400
        if not tipo_ajuda:
            return jsonify({"error": "Escolha um tipo de ajuda"}), 400

        cur.execute("""INSERT INTO PROJETOS (ID_USUARIOS, TITULO, DESCRICAO, CATEGORIA, 
                                             STATUS, TIPO_AJUDA, LOCALIZACAO)
                       VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING ID_PROJETOS""",
                    (id_usuarios, titulo, descricao, categoria, status, tipo_ajuda, localizacao))

        id_projetos = cur.fetchone()[0]
        con.commit()

        if foto_projeto:
            try:
                nome_imagem = f'{id_projetos}.jpeg'
                caminho_destino = os.path.join(app.config['UPLOAD_FOLDER'], 'Projetos')
                os.makedirs(caminho_destino, exist_ok=True)
                foto_projeto.save(os.path.join(caminho_destino, nome_imagem))
            except Exception as e:
                print(f"Erro ao salvar foto: {e}")

        return jsonify({'message': "Projeto cadastrado com sucesso!", 'id': id_projetos}), 201
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Listar projetos da ONG logada
# ============================================
@app.route('/listar_projetos', methods=['GET'])
def listar_projetos_ong():
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401

    id_usuarios = token_data['id_usuarios']

    con = conexao()
    cur = con.cursor()

    try:
        if token_data['tipo'] == 2:
            # ONG vê apenas seus projetos
            cur.execute("""SELECT ID_PROJETOS, ID_USUARIOS, TITULO, DESCRICAO, CATEGORIA, 
                                  STATUS, TIPO_AJUDA, LOCALIZACAO
                           FROM PROJETOS WHERE ID_USUARIOS = ? ORDER BY ID_PROJETOS DESC""", (id_usuarios,))
        else:
            # Outros veem todos os projetos
            cur.execute("""SELECT ID_PROJETOS, ID_USUARIOS, TITULO, DESCRICAO, CATEGORIA, 
                                  STATUS, TIPO_AJUDA, LOCALIZACAO
                           FROM PROJETOS ORDER BY ID_PROJETOS DESC""")

        projetos = cur.fetchall()

        lista_projetos = []
        for p in projetos:
            lista_projetos.append({
                'id': p[0],
                'id_usuarios': p[1],
                'titulo': p[2],
                'descricao': p[3],
                'categoria': p[4],
                'status': p[5],
                'tipo_ajuda': p[6],
                'localizacao': p[7],
                'foto': f'{p[0]}.jpeg'
            })

        return jsonify({'projetos': lista_projetos}), 200
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Buscar projeto por ID
# ============================================
@app.route('/buscar_projeto/<int:id_projetos>', methods=['GET'])
def buscar_projeto(id_projetos):
    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("""SELECT ID_PROJETOS, ID_USUARIOS, TITULO, DESCRICAO, CATEGORIA, 
                              STATUS, TIPO_AJUDA, LOCALIZACAO
                       FROM PROJETOS WHERE ID_PROJETOS = ?""", (id_projetos,))
        p = cur.fetchone()

        if not p:
            return jsonify({"error": "Projeto não encontrado"}), 404

        return jsonify({'projeto': {
            'id': p[0], 'id_usuarios': p[1], 'titulo': p[2], 'descricao': p[3],
            'categoria': p[4], 'status': p[5], 'tipo_ajuda': p[6], 'localizacao': p[7]
        }}), 200
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Editar projeto
# ============================================
@app.route('/editar_projeto/<int:id_projetos>', methods=['PUT'])
def editar_projeto(id_projetos):
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401

    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("SELECT ID_USUARIOS FROM PROJETOS WHERE ID_PROJETOS = ?", (id_projetos,))
        projeto = cur.fetchone()
        if not projeto:
            return jsonify({"error": "Projeto não encontrado"}), 404

        # Só dono ou ADM pode editar
        if token_data['tipo'] != 0 and token_data['id_usuarios'] != projeto[0]:
            return jsonify({'error': 'Sem permissão'}), 403

        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        categoria = request.form.get('categoria')
        tipo_ajuda = request.form.get('tipo_ajuda')
        localizacao = request.form.get('localizacao')
        status = request.form.get('status')
        foto_projeto = request.files.get('foto')

        cur.execute("""UPDATE PROJETOS SET TITULO = ?, DESCRICAO = ?, CATEGORIA = ?,
                       STATUS = ?, TIPO_AJUDA = ?, LOCALIZACAO = ?
                       WHERE ID_PROJETOS = ?""",
                    (titulo, descricao, categoria, status, tipo_ajuda, localizacao, id_projetos))
        con.commit()

        if foto_projeto:
            try:
                nome_imagem = f'{id_projetos}.jpeg'
                caminho_destino = os.path.join(app.config['UPLOAD_FOLDER'], 'Projetos')
                os.makedirs(caminho_destino, exist_ok=True)
                foto_projeto.save(os.path.join(caminho_destino, nome_imagem))
            except Exception as e:
                print(f"Erro ao salvar foto: {e}")

        return jsonify({'message': 'Projeto editado com sucesso!'}), 200
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTA: Deletar projeto
# ============================================
@app.route('/deletar_projeto/<int:id_projetos>', methods=['DELETE'])
def deletar_projeto(id_projetos):
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401

    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("SELECT ID_USUARIOS FROM PROJETOS WHERE ID_PROJETOS = ?", (id_projetos,))
        projeto = cur.fetchone()
        if not projeto:
            return jsonify({"error": "Projeto não encontrado"}), 404

        if token_data['tipo'] != 0 and token_data['id_usuarios'] != projeto[0]:
            return jsonify({'error': 'Sem permissão'}), 403

        cur.execute("DELETE FROM ATUALIZACOES WHERE ID_PROJETOS = ?", (id_projetos,))
        cur.execute("DELETE FROM PROJETOS WHERE ID_PROJETOS = ?", (id_projetos,))
        con.commit()

        return jsonify({'message': 'Projeto excluído com sucesso!'}), 200
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/ver_projeto_publico/<int:id_projetos>', methods=['GET'])
def ver_projeto_publico(id_projetos):
    con = conexao()
    cur = con.cursor()
    try:
        # Busca o projeto
        cur.execute("""SELECT ID_PROJETOS, ID_USUARIOS, TITULO, DESCRICAO, CATEGORIA, 
                              STATUS, TIPO_AJUDA, LOCALIZACAO
                       FROM PROJETOS WHERE ID_PROJETOS = ?""", (id_projetos,))
        p = cur.fetchone()
        if not p:
            return jsonify({"error": "Projeto não encontrado"}), 404

        # Busca a ONG
        cur.execute("""SELECT ID_USUARIOS, NOME, DESCRICAO_BREVE, CPF_CNPJ, 
                              COD_BANCO, NUM_AGENCIA, LOCALIZACAO
                       FROM USUARIOS WHERE ID_USUARIOS = ?""", (p[1],))
        ong = cur.fetchone()

        # Busca atualizações
        cur.execute("""SELECT ID_ATUALIZACOES, TITULO, TEXTO, DATA_CRIACAO
                       FROM ATUALIZACOES WHERE ID_PROJETOS = ? 
                       ORDER BY DATA_CRIACAO DESC""", (id_projetos,))
        atts = cur.fetchall()

        # Busca outros projetos da ONG
        cur.execute("""SELECT ID_PROJETOS, TITULO, DESCRICAO, TIPO_AJUDA
                       FROM PROJETOS WHERE ID_USUARIOS = ? AND ID_PROJETOS != ?""", (p[1], id_projetos))
        outros = cur.fetchall()

        return jsonify({
            'projeto': {
                'id': p[0], 'id_usuarios': p[1], 'titulo': p[2], 'descricao': p[3],
                'categoria': p[4], 'status': p[5], 'tipo_ajuda': p[6], 'localizacao': p[7]
            },
            'ong': {
                'id': ong[0], 'nome': ong[1], 'descricao_breve': ong[2],
                'cpf_cnpj': ong[3], 'cod_banco': ong[4], 'num_agencia': ong[5],
                'localizacao': ong[6]
            } if ong else None,
            'atualizacoes': [{
                'id': a[0], 'titulo': a[1], 'texto': a[2],
                'data': a[3].strftime('%d/%m/%Y %H:%M') if a[3] else ''
            } for a in atts] if atts else [],
            'projetos_ong': [{
                'id': o[0], 'titulo': o[1], 'descricao': o[2], 'tipo_ajuda': o[3]
            } for o in outros] if outros else []
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()


@app.route('/listar_projetos_publicos', methods=['GET'])
def listar_projetos_publicos():
    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT p.ID_PROJETOS, p.ID_USUARIOS, p.TITULO, p.DESCRICAO, p.CATEGORIA, 
                   p.STATUS, p.TIPO_AJUDA, p.LOCALIZACAO, u.NOME
            FROM PROJETOS p
            INNER JOIN USUARIOS u ON p.ID_USUARIOS = u.ID_USUARIOS
            WHERE u.APROVACAO = 1 AND u.ATIVO = 1 AND p.STATUS = 'Ativo'
            ORDER BY p.ID_PROJETOS DESC
        """)
        projetos = cur.fetchall()

        lista = []
        for p in projetos:
            lista.append({
                'id': p[0], 'id_usuarios': p[1], 'titulo': p[2], 'descricao': p[3],
                'categoria': p[4], 'status': p[5], 'tipo_ajuda': p[6], 'localizacao': p[7],
                'ong_nome': p[8], 'foto': f'{p[0]}.jpeg'
            })

        return jsonify({'projetos': lista}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()


