# ongs.py
from flask import jsonify, request, render_template
from funcao import enviando_email, decodificar_token
from main import app
from db import conexao
import threading
import datetime


def validar_adm():
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário. Faça login.'}), 401
    if token_data['tipo'] != 0:
        return jsonify({'error': 'Apenas administradores podem acessar esta rota'}), 403
    return None


# ============================================
# ROTAS PÚBLICAS
# ============================================

@app.route('/listar_ongs_publicas', methods=['GET'])
def listar_ongs_publicas():
    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT ID_USUARIOS, NOME, DESCRICAO_BREVE, CATEGORIA
            FROM USUARIOS 
            WHERE TIPO = 2 AND APROVACAO = 1 AND ATIVO = 1
            ORDER BY NOME
        """)
        ongs = cur.fetchall()
        lista = []
        if ongs:
            for o in ongs:
                lista.append({
                    'id': o[0],
                    'nome': o[1],
                    'descricao_breve': str(o[2]) if o[2] else '',
                    'categoria': str(o[3]) if o[3] else '',
                    'foto': f'{o[0]}.jpeg'
                })
        return jsonify({'ongs': lista}), 200
    except Exception as e:
        print(f"ERRO listar_ongs_publicas: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()




@app.route('/ver_ong_publica/<int:id_ong>', methods=['GET'])
def ver_ong_publica(id_ong):
    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("""SELECT ID_USUARIOS, NOME, DESCRICAO_BREVE, DESCRICAO_LONGA, 
                              CPF_CNPJ, CATEGORIA, LOCALIZACAO, COD_BANCO, NUM_AGENCIA
                       FROM USUARIOS WHERE ID_USUARIOS = ? AND TIPO = 2 AND APROVACAO = 1""", (id_ong,))
        ong = cur.fetchone()
        if not ong:
            return jsonify({"error": "ONG não encontrada"}), 404

        cur.execute("""SELECT ID_PROJETOS, TITULO, DESCRICAO, TIPO_AJUDA
                       FROM PROJETOS WHERE ID_USUARIOS = ? AND STATUS = 'Ativo'""", (id_ong,))
        projetos = cur.fetchall()

        return jsonify({
            'ong': {
                'id': ong[0], 'nome': ong[1], 'descricao_breve': ong[2],
                'descricao_longa': ong[3], 'cpf_cnpj': ong[4], 'categoria': ong[5],
                'localizacao': ong[6], 'cod_banco': ong[7], 'num_agencia': ong[8],
                'foto': f'{ong[0]}.jpeg'
            },
            'projetos': [{
                'id': p[0], 'titulo': p[1], 'descricao': p[2], 'tipo_ajuda': p[3]
            } for p in projetos] if projetos else []
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()


@app.route('/buscar', methods=['GET'])
def buscar():
    termo = request.args.get('q', '')
    tipo = request.args.get('tipo', 'todos')
    con = conexao()
    cur = con.cursor()
    resultado = {'ongs': [], 'projetos': []}
    try:
        if tipo in ['todos', 'ongs']:
            if termo:
                cur.execute("""SELECT ID_USUARIOS, NOME, DESCRICAO_BREVE, CATEGORIA FROM USUARIOS 
                               WHERE TIPO = 2 AND APROVACAO = 1 AND ATIVO = 1 
                               AND (NOME LIKE ? OR DESCRICAO_BREVE LIKE ? OR CATEGORIA LIKE ?)
                               ORDER BY NOME""", (f'%{termo}%', f'%{termo}%', f'%{termo}%'))
            else:
                cur.execute("""SELECT ID_USUARIOS, NOME, DESCRICAO_BREVE, CATEGORIA FROM USUARIOS 
                               WHERE TIPO = 2 AND APROVACAO = 1 AND ATIVO = 1 ORDER BY NOME""")
            ongs = cur.fetchall()
            resultado['ongs'] = [{'id': o[0], 'nome': o[1], 'descricao_breve': str(o[2]) if o[2] else '', 'categoria': str(o[3]) if o[3] else '', 'foto': f'{o[0]}.jpeg'} for o in ongs] if ongs else []

        if tipo in ['todos', 'projetos']:
            if termo:
                cur.execute("""SELECT p.ID_PROJETOS, p.TITULO, p.DESCRICAO, p.STATUS, p.CATEGORIA, u.NOME
                               FROM PROJETOS p INNER JOIN USUARIOS u ON p.ID_USUARIOS = u.ID_USUARIOS
                               WHERE u.APROVACAO = 1 AND u.ATIVO = 1 
                               AND (p.TITULO LIKE ? OR p.DESCRICAO LIKE ? OR p.CATEGORIA LIKE ?)
                               ORDER BY p.ID_PROJETOS DESC""", (f'%{termo}%', f'%{termo}%', f'%{termo}%'))
            else:
                cur.execute("""SELECT p.ID_PROJETOS, p.TITULO, p.DESCRICAO, p.STATUS, p.CATEGORIA, u.NOME
                               FROM PROJETOS p INNER JOIN USUARIOS u ON p.ID_USUARIOS = u.ID_USUARIOS
                               WHERE u.APROVACAO = 1 AND u.ATIVO = 1 ORDER BY p.ID_PROJETOS DESC""")
            projetos = cur.fetchall()
            resultado['projetos'] = [{'id': p[0], 'titulo': p[1], 'descricao': str(p[2]) if p[2] else '', 'status': str(p[3]) if p[3] else '', 'categoria': str(p[4]) if p[4] else '', 'ong_nome': str(p[5]) if p[5] else '', 'foto': f'{p[0]}.jpeg'} for p in projetos] if projetos else []

        return jsonify(resultado), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()


# ============================================
# ROTAS ADMINISTRATIVAS
# ============================================

@app.route('/admin/listar_ongs', methods=['GET'])
def listar_ongs():
    erro = validar_adm()
    if erro: return erro

    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("""SELECT ID_USUARIOS, NOME, EMAIL, CPF_CNPJ, TELEFONE,
                              DESCRICAO_BREVE, DESCRICAO_LONGA, APROVACAO, COD_BANCO,
                              NUM_AGENCIA, NUM_CONTA, TIPO_CONTA, CHAVE_PIX, CATEGORIA,
                              ATIVO, LOCALIZACAO, DATA_CADASTRO, EMAIL_CONFIRMACAO, MOTIVO_REPROVACAO
                       FROM USUARIOS WHERE TIPO = 2 ORDER BY DATA_CADASTRO DESC""")
        ongs = cur.fetchall()

        if not ongs:
            return jsonify({'message': 'Nenhuma ONG cadastrada', 'ongs': []}), 200

        lista_ongs = []
        for ong in ongs:
            status = 'Pendente' if ong[7] == 0 else 'Aprovada' if ong[7] == 1 else 'Reprovada' if ong[7] == 2 else 'Desconhecido'
            lista_ongs.append({
                'id': ong[0], 'nome': ong[1], 'email': ong[2], 'cpf_cnpj': ong[3],
                'telefone': ong[4], 'descricao_breve': ong[5], 'descricao_longa': ong[6],
                'status': status, 'codigo_aprovacao': ong[7], 'cod_banco': ong[8],
                'num_agencia': ong[9], 'num_conta': ong[10], 'tipo_conta': ong[11],
                'chave_pix': ong[12], 'categoria': ong[13], 'ativo': bool(ong[14]),
                'localizacao': ong[15],
                'data_cadastro': ong[16].strftime('%d/%m/%Y %H:%M:%S') if ong[16] else None,
                'email_confirmado': bool(ong[17]),
                'motivo_reprovacao': ong[18] if len(ong) > 18 and ong[18] else None
            })

        return jsonify({'message': 'ONGs listadas', 'total': len(lista_ongs), 'ongs': lista_ongs}), 200
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/admin/buscar_ong', methods=['GET'])
def buscar_ong():
    erro = validar_adm()
    if erro: return erro

    ong_id = request.args.get('id')
    if not ong_id:
        return jsonify({'error': 'Forneça um ID'}), 400

    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("""SELECT ID_USUARIOS, NOME, EMAIL, CPF_CNPJ, TELEFONE,
                              DESCRICAO_BREVE, DESCRICAO_LONGA, APROVACAO, COD_BANCO,
                              NUM_AGENCIA, NUM_CONTA, TIPO_CONTA, CHAVE_PIX, CATEGORIA,
                              ATIVO, LOCALIZACAO, DATA_CADASTRO, EMAIL_CONFIRMACAO, MOTIVO_REPROVACAO
                       FROM USUARIOS WHERE TIPO = 2 AND ID_USUARIOS = ?""", (ong_id,))
        ong = cur.fetchone()
        if not ong:
            return jsonify({'error': 'ONG não encontrada'}), 404

        status = 'Pendente' if ong[7] == 0 else 'Aprovada' if ong[7] == 1 else 'Reprovada' if ong[7] == 2 else 'Desconhecido'
        return jsonify({'ong': {
            'id': ong[0], 'nome': ong[1], 'email': ong[2], 'cpf_cnpj': ong[3],
            'telefone': ong[4], 'descricao_breve': ong[5], 'descricao_longa': ong[6],
            'status': status, 'codigo_aprovacao': ong[7], 'cod_banco': ong[8],
            'num_agencia': ong[9], 'num_conta': ong[10], 'tipo_conta': ong[11],
            'chave_pix': ong[12], 'categoria': ong[13], 'ativo': bool(ong[14]),
            'localizacao': ong[15],
            'data_cadastro': ong[16].strftime('%d/%m/%Y %H:%M:%S') if ong[16] else None,
            'email_confirmado': bool(ong[17]),
            'motivo_reprovacao': ong[18] if len(ong) > 18 and ong[18] else None
        }}), 200
    except Exception as e:
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/admin/aprovar_ong/<int:id_usuarios>', methods=['PUT'])
def aprovar_ong(id_usuarios):
    erro = validar_adm()
    if erro: return erro

    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("SELECT ID_USUARIOS, NOME, EMAIL, APROVACAO FROM USUARIOS WHERE ID_USUARIOS = ? AND TIPO = 2", (id_usuarios,))
        ong = cur.fetchone()
        if not ong: return jsonify({'error': 'ONG não encontrada'}), 404
        if ong[3] == 1: return jsonify({'message': 'ONG já está aprovada'}), 200

        cur.execute("UPDATE USUARIOS SET APROVACAO = 1, MOTIVO_REPROVACAO = NULL WHERE ID_USUARIOS = ?", (id_usuarios,))
        con.commit()

        html = render_template('template_aprovacao.html', nome=ong[1], mensagem=f'Parabéns {ong[1]}! Sua ONG foi aprovada.')
        threading.Thread(target=enviando_email, args=(ong[2], 'ONG Aprovada - Doar +', html)).start()

        return jsonify({'message': f'ONG {ong[1]} aprovada!', 'id': id_usuarios}), 200
    except Exception as e:
        con.rollback()
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/admin/reprovar_ong/<int:id_usuarios>', methods=['PUT'])
def reprovar_ong(id_usuarios):
    erro = validar_adm()
    if erro: return erro

    motivo = request.json.get('motivo', 'Não especificado')
    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("SELECT ID_USUARIOS, NOME, EMAIL, APROVACAO FROM USUARIOS WHERE ID_USUARIOS = ? AND TIPO = 2", (id_usuarios,))
        ong = cur.fetchone()
        if not ong: return jsonify({'error': 'ONG não encontrada'}), 404
        if ong[3] == 2: return jsonify({'message': 'ONG já está reprovada'}), 200

        cur.execute("UPDATE USUARIOS SET APROVACAO = 2, MOTIVO_REPROVACAO = ? WHERE ID_USUARIOS = ?", (motivo, id_usuarios))
        con.commit()

        html = render_template('template_reprovacao.html', nome=ong[1], mensagem=f'Olá {ong[1]}, sua ONG não foi aprovada.', motivo=motivo)
        threading.Thread(target=enviando_email, args=(ong[2], 'Atualização ONG - Doar +', html)).start()

        return jsonify({'message': f'ONG {ong[1]} reprovada', 'motivo': motivo}), 200
    except Exception as e:
        con.rollback()
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/admin/bloquear_ong/<int:id_usuarios>', methods=['PUT'])
def bloquear_ong(id_usuarios):
    erro = validar_adm()
    if erro: return erro

    acao = request.json.get('acao', 'bloquear')
    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("SELECT ID_USUARIOS, NOME FROM USUARIOS WHERE ID_USUARIOS = ? AND TIPO = 2", (id_usuarios,))
        ong = cur.fetchone()
        if not ong: return jsonify({'error': 'ONG não encontrada'}), 404

        novo_status = 0 if acao == 'bloquear' else 1
        cur.execute("UPDATE USUARIOS SET ATIVO = ? WHERE ID_USUARIOS = ?", (novo_status, id_usuarios))
        con.commit()
        return jsonify({'message': f'ONG {ong[1]} {"bloqueada" if acao == "bloquear" else "desbloqueada"}!'}), 200
    except Exception as e:
        con.rollback()
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/admin/deletar_ong/<int:id_usuarios>', methods=['DELETE'])
def deletar_ong(id_usuarios):
    erro = validar_adm()
    if erro: return erro

    con = conexao()
    cur = con.cursor()
    try:
        cur.execute("SELECT ID_USUARIOS, NOME, ATIVO, APROVACAO FROM USUARIOS WHERE ID_USUARIOS = ? AND TIPO = 2", (id_usuarios,))
        ong = cur.fetchone()
        if not ong: return jsonify({'error': 'ONG não encontrada'}), 404
        if ong[2] == 1 and ong[3] != 2:
            return jsonify({'error': 'Apenas ONGs bloqueadas ou reprovadas podem ser excluídas'}), 403

        cur.execute("DELETE FROM HISTORICO_SENHA WHERE ID_USUARIOS = ?", (id_usuarios,))
        cur.execute("DELETE FROM RECUPERACAO_SENHA WHERE ID_USUARIOS = ?", (id_usuarios,))
        cur.execute("DELETE FROM USUARIOS WHERE ID_USUARIOS = ?", (id_usuarios,))
        con.commit()
        return jsonify({'message': f'ONG {ong[1]} excluída!'}), 200
    except Exception as e:
        con.rollback()
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/ong/editar_perfil/<int:id_usuarios>', methods=['PUT'])
def editar_perfil_ong(id_usuarios):
    con = conexao()
    cur = con.cursor()
    try:
        token_data = decodificar_token()
        if token_data == False:
            return jsonify({'error': 'Token necessário'}), 401
        if token_data['id_usuarios'] != id_usuarios:
            return jsonify({'error': 'Você só pode editar seu próprio perfil'}), 403
        if token_data['tipo'] != 2:
            return jsonify({'error': 'Apenas ONGs podem acessar esta rota'}), 403

        cur.execute("SELECT * FROM USUARIOS WHERE ID_USUARIOS = ? AND TIPO = 2", (id_usuarios,))
        ong_atual = cur.fetchone()
        if not ong_atual:
            return jsonify({'error': 'ONG não encontrada'}), 404

        nome = request.form.get('nome', ong_atual[1])
        email = request.form.get('email', ong_atual[2])
        cpf_cnpj = request.form.get('cpf_cnpj', ong_atual[4])
        telefone = request.form.get('telefone', ong_atual[5])
        descricao_breve = request.form.get('descricao_breve', ong_atual[6])
        descricao_longa = request.form.get('descricao_longa', ong_atual[7])
        cod_banco = request.form.get('cod_banco', ong_atual[9])
        num_agencia = request.form.get('num_agencia', ong_atual[10])
        num_conta = request.form.get('num_conta', ong_atual[11])
        tipo_conta = request.form.get('tipo_conta', ong_atual[12])
        chave_pix = request.form.get('chave_pix', ong_atual[13])
        categoria = request.form.get('categoria', ong_atual[14])
        localizacao = request.form.get('localizacao', ong_atual[16])
        senha = request.form.get('senha', None)
        confirmar_senha = request.form.get('confirmar_senha', None)

        from flask_bcrypt import generate_password_hash
        from funcao import senha_forte, senha_correspondente, senha_antiga

        nova_senha_hash = ong_atual[3]
        if senha:
            if not senha_correspondente(senha, confirmar_senha):
                return jsonify({'error': 'Senhas não correspondem'}), 400
            nova_senha_hash = generate_password_hash(senha).decode('utf-8')

        cur.execute("""UPDATE USUARIOS SET NOME=?, EMAIL=?, SENHA=?, CPF_CNPJ=?, TELEFONE=?,
                       DESCRICAO_BREVE=?, DESCRICAO_LONGA=?, COD_BANCO=?, NUM_AGENCIA=?,
                       NUM_CONTA=?, TIPO_CONTA=?, CHAVE_PIX=?, CATEGORIA=?, LOCALIZACAO=?
                       WHERE ID_USUARIOS=?""",
                    (nome, email, nova_senha_hash, cpf_cnpj, telefone, descricao_breve,
                     descricao_longa, cod_banco, num_agencia, num_conta, tipo_conta,
                     chave_pix, categoria, localizacao, id_usuarios))
        con.commit()
        return jsonify({'message': 'Perfil atualizado com sucesso!'}), 200
    except Exception as e:
        con.rollback()
        return jsonify({'error': f'Erro: {str(e)}'}), 500
    finally:
        cur.close()
        con.close()