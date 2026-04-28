from flask import jsonify, request, make_response, render_template
from funcao import senha_forte, enviando_email, gerar_token, verificar_existente, senha_correspondente, senha_antiga, decodificar_token
from flask_bcrypt import generate_password_hash, check_password_hash
from main import app
from db import conexao
import threading
import os
import datetime
from random import randint


# Criar usuário
# Criar usuário
@app.route('/criar_usuarios', methods=['POST'])
def criar_usuarios():
    nome = request.form.get('nome', None)
    email = request.form.get('email', None)
    cpf_cnpj = request.form.get('cpf_cnpj', None)
    telefone = request.form.get('telefone', None)
    descricao_breve = request.form.get('descricao_breve', None)
    descricao_longa = request.form.get('descricao_longa', None)
    cod_banco = request.form.get('cod_banco', None)
    num_agencia = request.form.get('num_agencia', None)
    num_conta = request.form.get('num_conta', None)
    tipo_conta = request.form.get('tipo_conta', None)
    chave_pix = request.form.get('chave_pix', None)
    categoria = request.form.get('categoria', None)
    localizacao = request.form.get('localizacao', None)
    senha = request.form.get('senha')
    confirmar_senha = request.form.get('confirmar_senha')
    tipo = request.form.get('tipo', 1)

    try:
        tipo = int(tipo)
    except (ValueError, TypeError):
        tipo = 1

    foto_perfil = request.files.get('foto_perfil')
    data_cadastro = datetime.datetime.now()
    ativo = 1

    if tipo == 2:
        aprovacao = 0
    else:
        aprovacao = None

    email_confirmacao = 0

    # Só ADM pode criar outro ADM
    if tipo == 0:
        token_data = decodificar_token()
        if token_data == False or token_data['tipo'] != 0:
            return jsonify({'error': 'Apenas administradores podem criar contas de ADM'}), 403

    con = conexao()
    cur = con.cursor()

    try:
        if nome == None or nome.strip() == '':
            return jsonify({"error": "Nome é obrigatório"}), 400
        if cpf_cnpj == None or cpf_cnpj.strip() == '':
            return jsonify({"error": "CPF/CNPJ é obrigatório"}), 400
        if email == None or email.strip() == '':
            return jsonify({"error": "E-mail é obrigatório"}), 400
        if verificar_existente(cpf_cnpj, 1) == False:
            return jsonify({"error": "CPF ou CNPJ já cadastrado"}), 400
        if verificar_existente(email, 2) == False:
            return jsonify({"error": "E-mail já cadastrado"}), 400
        if senha_forte(senha) == False:
            return jsonify({"error": "Senha fraca"}), 400
        if senha_correspondente(senha, confirmar_senha) == False:
            return jsonify({"error": "Senhas não correspondem"}), 400

        senha_cripto = generate_password_hash(senha).decode('utf-8')
        codigo_confirmacao = randint(100000, 999999)
        tentativa = 0

        cur.execute("""INSERT INTO USUARIOS (NOME, EMAIL, SENHA, CPF_CNPJ, TELEFONE,
                                             DESCRICAO_BREVE, DESCRICAO_LONGA, APROVACAO,
                                             COD_BANCO, NUM_AGENCIA, NUM_CONTA, TIPO_CONTA,
                                             CHAVE_PIX, CATEGORIA, ATIVO, LOCALIZACAO,
                                             TIPO, DATA_CADASTRO, EMAIL_CONFIRMACAO,
                                             CODIGO_CONFIRMACAO, TENTATIVA)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING ID_USUARIOS""",
                    (nome, email, senha_cripto, cpf_cnpj, telefone, descricao_breve,
                     descricao_longa, aprovacao, cod_banco, num_agencia, num_conta, tipo_conta,
                     chave_pix, categoria, ativo, localizacao, tipo, data_cadastro, email_confirmacao,
                     codigo_confirmacao, tentativa))

        codigo_usuarios = cur.fetchone()[0]
        con.commit()

        if foto_perfil:
            try:
                nome_imagem = f'{codigo_usuarios}.jpeg'
                caminho_imagem_destino = os.path.join(app.config['UPLOAD_FOLDER'], 'Usuarios')
                os.makedirs(caminho_imagem_destino, exist_ok=True)
                caminho_imagem = os.path.join(caminho_imagem_destino, nome_imagem)
                foto_perfil.save(caminho_imagem)
            except Exception as e:
                print(f"ERRO ao salvar imagem: {e}")

        assunto = 'Código de Confirmação de E-mail'
        mensagem = 'Bem-vindo(a) à Doar +! Confirme seu e-mail.'
        codigo = codigo_confirmacao
        html = render_template('template_email.html', mensagem=mensagem, codigo=codigo)
        threading.Thread(target=enviando_email, args=(email, assunto, html)).start()

        return jsonify(
            {'message': "Usuário cadastrado com sucesso", 'usuario': {'tipo': tipo, 'nome': nome, 'email': email}}), 201

    except Exception as e:
        print(f"ERRO ao cadastrar usuário: {e}")
        return jsonify({'message': f'Erro: {e}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/editar_usuarios/<int:id_usuarios>', methods=['PUT'])
def editar_usuarios(id_usuarios):
    con = None
    cur = None

    try:
        con = conexao()
        cur = con.cursor()

        # Pega o token do FormData
        token = request.form.get('token', None)
        if token is None:
            return jsonify({'error': 'Token necessário'}), 401

        # Verifica se o token é válido
        from funcao import decodificar_token
        import jwt
        from flask import current_app

        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            token_tipo = payload['tipo']
            token_id = payload['id_usuarios']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expirado. Faça login novamente.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token inválido.'}), 401

        # Apenas ADM (tipo 0) ou o próprio usuário pode editar
        if token_tipo != 0 and token_id != id_usuarios:
            return jsonify({'error': 'Você não tem permissão para editar este usuário'}), 403

        # Busca dados atuais do usuário
        cur.execute("""
            SELECT NOME, EMAIL, SENHA, CPF_CNPJ, TELEFONE,
                   DESCRICAO_BREVE, DESCRICAO_LONGA, APROVACAO,
                   COD_BANCO, NUM_AGENCIA, NUM_CONTA, TIPO_CONTA,
                   CHAVE_PIX, CATEGORIA, ATIVO, LOCALIZACAO, TIPO,
                   DATA_CADASTRO, EMAIL_CONFIRMACAO, CODIGO_CONFIRMACAO, TENTATIVA
            FROM USUARIOS
            WHERE ID_USUARIOS = ?
        """, (id_usuarios,))

        tem_usuario = cur.fetchone()
        if tem_usuario is None:
            return jsonify({"error": "Usuário não encontrado"}), 404

        # Pega os dados do formulário ou mantém os atuais
        nome = request.form.get('nome', tem_usuario[0])
        email = request.form.get('email', tem_usuario[1])
        cpf_cnpj = request.form.get('cpf_cnpj', tem_usuario[3])
        telefone = request.form.get('telefone', tem_usuario[4])
        descricao_breve = request.form.get('descricao_breve', tem_usuario[5])
        descricao_longa = request.form.get('descricao_longa', tem_usuario[6])
        cod_banco = request.form.get('cod_banco', tem_usuario[8])
        num_agencia = request.form.get('num_agencia', tem_usuario[9])
        num_conta = request.form.get('num_conta', tem_usuario[10])
        tipo_conta = request.form.get('tipo_conta', tem_usuario[11])
        chave_pix = request.form.get('chave_pix', tem_usuario[12])
        categoria = request.form.get('categoria', tem_usuario[13])
        localizacao = request.form.get('localizacao', tem_usuario[15])
        senha = request.form.get('senha', None)
        confirmar_senha = request.form.get('confirmar_senha', None)
        foto_perfil = request.files.get('foto_perfil')

        # Validações básicas
        if not nome or nome.strip() == '':
            return jsonify({"error": "Nome é obrigatório"}), 400

        if not email or email.strip() == '':
            return jsonify({"error": "Email é obrigatório"}), 400

        # Verifica duplicidade de CPF/CNPJ (se foi alterado)
        if cpf_cnpj != tem_usuario[3]:
            cur.execute("SELECT ID_USUARIOS FROM USUARIOS WHERE CPF_CNPJ = ? AND ID_USUARIOS != ?",
                        (cpf_cnpj, id_usuarios))
            if cur.fetchone():
                return jsonify({"error": "CPF/CNPJ já cadastrado"}), 400

        # Verifica duplicidade de email (se foi alterado)
        if email != tem_usuario[1]:
            cur.execute("SELECT ID_USUARIOS FROM USUARIOS WHERE EMAIL = ? AND ID_USUARIOS != ?", (email, id_usuarios))
            if cur.fetchone():
                return jsonify({"error": "E-mail já cadastrado"}), 400

        # Trata senha (opcional)
        nova_senha_hash = tem_usuario[2]
        if senha:
            if senha != confirmar_senha:
                return jsonify({"error": "Senhas não correspondem"}), 400

            from flask_bcrypt import generate_password_hash
            nova_senha_hash = generate_password_hash(senha).decode('utf-8')

        # Atualiza no banco
        cur.execute("""
            UPDATE USUARIOS
            SET NOME = ?,
                EMAIL = ?,
                SENHA = ?,
                CPF_CNPJ = ?,
                TELEFONE = ?,
                DESCRICAO_BREVE = ?,
                DESCRICAO_LONGA = ?,
                COD_BANCO = ?,
                NUM_AGENCIA = ?,
                NUM_CONTA = ?,
                TIPO_CONTA = ?,
                CHAVE_PIX = ?,
                CATEGORIA = ?,
                LOCALIZACAO = ?
            WHERE ID_USUARIOS = ?
        """, (
            nome, email, nova_senha_hash, cpf_cnpj, telefone,
            descricao_breve, descricao_longa, cod_banco, num_agencia,
            num_conta, tipo_conta, chave_pix, categoria, localizacao,
            id_usuarios
        ))

        con.commit()

        # Salva foto de perfil se enviada
        if foto_perfil:
            try:
                nome_imagem = f'{id_usuarios}.jpeg'
                caminho_pasta = os.path.join(app.config['UPLOAD_FOLDER'], 'Usuarios')
                os.makedirs(caminho_pasta, exist_ok=True)
                caminho_imagem = os.path.join(caminho_pasta, nome_imagem)
                foto_perfil.save(caminho_imagem)
                print(f"DEBUG - Foto atualizada: {caminho_imagem}")
            except Exception as e:
                print(f"ERRO ao salvar foto: {e}")

        return jsonify({'message': 'Editado com sucesso!'}), 200

    except Exception as e:
        print(f"ERRO editar_usuarios: {e}")
        if con:
            try:
                con.rollback()
            except:
                pass
        return jsonify({'message': f'Erro ao editar: {str(e)}'}), 500
    finally:
        if cur:
            try:
                cur.close()
            except:
                pass
        if con:
            try:
                con.close()
            except:
                pass


# Excluir usuário
@app.route('/deletar_usuarios/<int:id_usuarios>', methods=['DELETE'])
def deletar_usuarios(id_usuarios):
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401

    # Apenas ADM ou o próprio usuário pode excluir
    if token_data['tipo'] != 0 and token_data['id_usuarios'] != id_usuarios:
        return jsonify({'error': 'Você não tem permissão para excluir este usuário'}), 403

    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("SELECT ID_USUARIOS FROM USUARIOS WHERE ID_USUARIOS = ?", (id_usuarios,))
        if not cur.fetchone():
            return jsonify({"error": "Usuário não encontrado"}), 404

        cur.execute("DELETE FROM HISTORICO_SENHA WHERE ID_USUARIOS = ?", (id_usuarios,))
        cur.execute("DELETE FROM RECUPERACAO_SENHA WHERE ID_USUARIOS = ?", (id_usuarios,))
        cur.execute("DELETE FROM USUARIOS WHERE ID_USUARIOS = ?", (id_usuarios,))
        con.commit()

        return jsonify({"message": "Usuário excluído com sucesso"}), 200

    except Exception as e:
        return jsonify({'message': f'Erro: {e}'}), 500
    finally:
        cur.close()
        con.close()


# Ativar usuário
@app.route('/ativar_usuarios/<int:id_usuarios>', methods=['PUT'])
def ativar_usuarios(id_usuarios):
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401
    if token_data['tipo'] != 0:
        return jsonify({'error': 'Apenas administradores podem ativar usuários'}), 403

    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("UPDATE USUARIOS SET ATIVO = 1 WHERE ID_USUARIOS = ?", (id_usuarios,))
        con.commit()
        return jsonify({'message': 'Usuário ativado com sucesso!'}), 200
    finally:
        cur.close()
        con.close()


# Inativar usuário
@app.route('/inativar_usuarios/<int:id_usuarios>', methods=['PUT'])
def inativar_usuarios(id_usuarios):
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401
    if token_data['tipo'] != 0 and token_data['id_usuarios'] != id_usuarios:
        return jsonify({'error': 'Você não tem permissão para inativar este usuário'}), 403

    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("SELECT ID_USUARIOS FROM USUARIOS WHERE ID_USUARIOS = ?", (id_usuarios,))
        if not cur.fetchone():
            return jsonify({"error": "Usuário não encontrado"}), 404

        cur.execute("UPDATE USUARIOS SET ATIVO = 0 WHERE ID_USUARIOS = ?", (id_usuarios,))
        con.commit()
        return jsonify({"message": "Usuário inativado com sucesso"}), 200
    except Exception as e:
        return jsonify({'message': f'Erro: {e}'}), 500
    finally:
        cur.close()
        con.close()


# Listar usuários
@app.route('/listar_usuarios', methods=['GET'])
def listar_usuarios():
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401
    if token_data['tipo'] != 0:
        return jsonify({'error': 'Apenas administradores podem listar usuários'}), 403

    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("""SELECT ID_USUARIOS, NOME, EMAIL, SENHA, CPF_CNPJ, TELEFONE,
                              DESCRICAO_BREVE, DESCRICAO_LONGA, APROVACAO, COD_BANCO,
                              NUM_AGENCIA, NUM_CONTA, TIPO_CONTA, CHAVE_PIX, CATEGORIA,
                              ATIVO, LOCALIZACAO, TIPO, DATA_CADASTRO, EMAIL_CONFIRMACAO,
                              CODIGO_CONFIRMACAO, TENTATIVA
                       FROM USUARIOS""")
        usuarios = cur.fetchall()
        if usuarios:
            return jsonify({'usuarios': usuarios}), 200
        else:
            return jsonify({'error': 'Nenhum usuário encontrado'}), 404
    except Exception as e:
        return jsonify({'message': f'Erro: {e}'}), 500
    finally:
        cur.close()
        con.close()


# Buscar usuários por CPF/CNPJ
@app.route('/buscar_usuarios', methods=['GET'])
def buscar_usuarios():
    # Pega valor de busca
    cpf_cnpj = request.json.get('cpf_cnpj')

    # Cria conexão
    con = conexao()

    # Abre cursor
    cur = con.cursor()

    try:
        # Verifica token
        if decodificar_token() == False:
            return jsonify({'error': 'Token necessário'}), 401

        # Apenas administrador pode buscar
        if decodificar_token()['tipo'] != 0:
            return jsonify({'error': 'É necessário ser administrador para isso'}), 401

        # Adiciona o % antes e depois pra poder buscar mesmo se não for o valor completo
        valor_busca = f"%{cpf_cnpj}%"

        # Executa consulta
        cur.execute("""SELECT ID_USUARIOS,
                              NOME,
                              EMAIL,
                              SENHA,
                              CPF_CNPJ,
                              TELEFONE,
                              DESCRICAO_BREVE,
                              DESCRICAO_LONGA,
                              APROVACAO,
                              COD_BANCO,
                              NUM_AGENCIA,
                              NUM_CONTA,
                              TIPO_CONTA,
                              CHAVE_PIX,
                              CATEGORIA,
                              ATIVO,
                              LOCALIZACAO,
                              TIPO,
                              DATA_CADASTRO,
                              EMAIL_CONFIRMACAO,
                              CODIGO_CONFIRMACAO,
                              TENTATIVA
                       FROM USUARIOS
                       WHERE cpf_cnpj LIKE ?""", (valor_busca,))

        # Armazena resultado
        usuarios = cur.fetchall()

        # Retorna resultado
        if usuarios:
            return jsonify({'usuarios': usuarios}), 200
        else:
            return jsonify({
                'error': 'Não foi possível encontrar usuários com esse cpf/cnpj'
            }), 404

    except Exception as e:
        return jsonify({'message': f'Erro ao consultar o banco de dados: {e}'}), 500
    finally:
        cur.close()
        con.close()


@app.route('/login', methods=['POST'])
def login():
    cpf_cnpj = request.json.get('cpf_cnpj')
    senha = request.json.get('senha')

    # Verifica se já está logado
    if decodificar_token() != False:
        return jsonify({'error': 'Você já está logado. Faça logout primeiro.'}), 400

    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("""SELECT ID_USUARIOS, TIPO, NOME, CPF_CNPJ, SENHA, TENTATIVA,
                              EMAIL_CONFIRMACAO, ATIVO, APROVACAO
                       FROM USUARIOS WHERE CPF_CNPJ = ?""", (cpf_cnpj,))

        usuario = cur.fetchone()
        if not usuario:
            return jsonify({"error": "Usuário não encontrado"}), 404

        id_usuarios = usuario[0]
        tipo = usuario[1]
        nome = usuario[2]
        senha_hash = usuario[4]
        tentativa = usuario[5]
        email_confirmacao = usuario[6]
        ativo = usuario[7]
        aprovacao = usuario[8]

        if tentativa > 3 and tipo != 0:
            return jsonify({"error": "Usuário bloqueado! Contate o administrador"}), 400
        if ativo == 0:
            return jsonify({"error": "Usuário inativado"}), 400
        if email_confirmacao == 0:
            return jsonify({"error": "Verifique o e-mail antes de logar!"}), 400
        if tipo == 2:
            if aprovacao == 0:
                return jsonify({"error": "Sua ONG ainda está pendente de aprovação"}), 400
            elif aprovacao == 2:
                return jsonify({"error": "Sua ONG foi reprovada. Contate o administrador"}), 400

        if check_password_hash(senha_hash, senha):
            if tentativa > 0:
                cur.execute("UPDATE USUARIOS SET TENTATIVA = 0 WHERE ID_USUARIOS = ?", (id_usuarios,))
                con.commit()

            token = gerar_token(tipo, id_usuarios, 10)
            resp = make_response(jsonify({'message': f'Bem-vindo {nome}!', 'nome': nome, 'token': token}))
            resp.set_cookie('acess_token', token, httponly=True, secure=False, samesite='Lax', path="/", max_age=3600)
            return resp

        if tipo != 0:
            tentativa = tentativa + 1
            cur.execute("UPDATE USUARIOS SET TENTATIVA = ? WHERE ID_USUARIOS = ?", (tentativa, id_usuarios))
            con.commit()

        return jsonify({"error": "Senha incorreta"}), 400

    except Exception as e:
        return jsonify({'message': f'Erro: {e}'}), 500
    finally:
        cur.close()
        con.close()

# Logout
@app.route('/logout', methods=['POST'])
def logout():
    if decodificar_token() == False:
        return jsonify({'message': 'Você já está deslogado!'})

    resp = make_response(jsonify({'message': 'Deslogado com sucesso!'}))
    resp.set_cookie('acess_token', '', httponly=True, secure=False, samesite='None', path="/", max_age=0)
    return resp


# Desbloquear usuário
@app.route('/desbloquear_usuarios/<int:id_usuarios>', methods=['PUT'])
def desbloquear_usuarios(id_usuarios):
    # Cria conexão
    con = conexao()

    # Abre cursor
    cur = con.cursor()

    try:
        # Verifica token
        if decodificar_token() == False:
            return jsonify({'error': 'Token necessário'}), 401

        # Apenas administrador pode desbloquear
        if decodificar_token()['tipo'] == 0:
            tentativa = 0

            # Zera tentativas
            cur.execute("""UPDATE USUARIOS
                           SET TENTATIVA = ?
                           WHERE ID_USUARIOS = ?""", (tentativa, id_usuarios))

            con.commit()

            return jsonify({'message': 'Usuário desbloqueado com sucesso!'})

        return jsonify({'error': 'É necessário ser administrador'})
    finally:
        cur.close()
        con.close()


# Confirmar e-mail
@app.route('/confirmar_email', methods=['POST'])
def confirmar_email():
    # Pega código digitado
    codigo_digitado = (request.json.get('codigo_digitado'))

    # Cria conexão
    con = conexao()

    # Abre cursor
    cursor = con.cursor()

    # Verifica se código foi enviado
    if not codigo_digitado:
        return jsonify({'error': 'Preencha o código de confirmação'}), 400

    try:
        # Busca usuário pelo código
        cursor.execute('SELECT id_usuarios FROM usuarios WHERE codigo_confirmacao = ?', (str(codigo_digitado, ),))
        usuario = cursor.fetchone()

        # Verifica se código é válido
        if not usuario:
            return jsonify({'error': 'Código incorreto'}), 404

        id_usuarios = usuario[0]

        # Atualiza confirmação de e-mail
        cursor.execute('UPDATE usuarios SET email_confirmacao = 1, codigo_confirmacao = NULL WHERE id_usuarios = ?',
                       (id_usuarios, ))

        con.commit()

        return jsonify({'message': 'Email confirmado com sucesso!'}), 200

    except Exception as e:
        return jsonify({'error': f'Erro: {e}'})
    finally:
        cursor.close()
        con.close()


# Esqueci senha
@app.route('/esqueci_senha', methods=['POST'])
def esqueci_senha():
    # Pega e-mail
    email = request.json.get('email')

    # Verifica se foi enviado
    if not email:
        return jsonify({'error': "Por favor, envie o e-mail."}), 400

    # Cria conexão
    con = conexao()

    # Abre cursor
    cursor = con.cursor()

    try:
        # Busca usuário e verifica se está ativo
        cursor.execute("SELECT id_usuarios, NOME, ATIVO FROM usuarios WHERE EMAIL = ?", (email,))
        usuario = cursor.fetchone()

        # Verifica se usuário existe
        if not usuario:
            return jsonify({'error': "Usuário não encontrado"}), 404

        id_usuarios = usuario[0]
        nome = usuario[1]
        ativo = usuario[2]

        # Verifica se está ativo
        if ativo == 0:
            return jsonify({"error": "Esse usuário está inativado"}), 403

        # Busca código de recuperação existente
        cursor.execute("""SELECT CODIGO, DATA_EXPIRACAO
                          FROM RECUPERACAO_SENHA
                          WHERE ID_usuarios = ?""", (id_usuarios,))

        # Armazena resultado
        dados_recuperacao = cursor.fetchone()

        # Se já existir código válido, reutiliza
        if dados_recuperacao and dados_recuperacao[1] > datetime.datetime.now():
            codigo = dados_recuperacao[0]

            assunto = 'Código de Recuperação de Senha'
            mensagem = 'Recebemos uma solicitação para recuperar sua senha'

            html = render_template('template_email.html', mensagem=mensagem, codigo=codigo)

            # Reenvia código
            threading.Thread(target=enviando_email,
                             args=(email, assunto, html)
                             ).start()

            return jsonify({
                'message': "Percebemos que seu código ainda está ativo, por isso ele foi reenviado para o e-mail!"}), 200

        # Remove códigos antigos
        cursor.execute("DELETE FROM RECUPERACAO_SENHA WHERE id_usuarios = ?", (id_usuarios,))

        # Gera novo código
        codigo = randint(100000, 999999)

        # Define validade (30 minutos)
        validade = datetime.datetime.now() + datetime.timedelta(minutes=30)

        # Insere novo código
        cursor.execute("""
                       INSERT INTO RECUPERACAO_SENHA (id_usuarios, CODIGO, DATA_EXPIRACAO)
                       VALUES (?, ?, ?)
                       """, (id_usuarios, codigo, validade))

        con.commit()

        # Prepara envio de e-mail
        assunto = 'Código de Recuperação de Senha'
        mensagem = 'Recebemos uma solicitação para recuperar sua senha'

        html = render_template('template_email.html', mensagem=mensagem, codigo=codigo)

        # Envia e-mail
        threading.Thread(target=enviando_email,
                         args=(email, assunto, html)
                         ).start()

        return jsonify({'message': "Código enviado para o e-mail!"}), 200

    except Exception as e:
        con.rollback()
        return jsonify({'error': f"Erro interno: {e}"}), 500
    finally:
        cursor.close()
        con.close()


# Verificar código de recuperação
@app.route('/verificar_codigo', methods=['POST'])
def verificar_codigo():
    # Pega código digitado
    codigo_digitado = request.json.get('codigo_digitado')

    # Verifica se foi enviado
    if not codigo_digitado:
        return jsonify({'error': 'Preencha o código'}), 400

    # Cria conexão
    con = conexao()

    # Abre cursor
    cursor = con.cursor()

    try:
        # Busca código no banco
        cursor.execute('SELECT id_usuarios, data_expiracao FROM RECUPERACAO_SENHA WHERE codigo = ?', (codigo_digitado,))
        recuperacao = cursor.fetchone()

        # Verifica se código existe
        if not recuperacao:
            return jsonify({'error': 'Código incorreto!'}), 404

        id_usuarios = recuperacao[0]
        data_expiracao = recuperacao[1]

        # Verifica se código expirou
        if datetime.datetime.now() > data_expiracao:
            cursor.execute("DELETE FROM RECUPERACAO_SENHA WHERE id_usuarios = ?", (id_usuarios,))
            con.commit()
            return jsonify({'message': "Este código expirou. Solicite um novo."}), 400

        # Busca tipo do usuário
        cursor.execute("SELECT TIPO FROM USUARIOS WHERE ID_USUARIOS = ?", (id_usuarios,))
        tipo = cursor.fetchone()[0]

        # Gera token temporário
        token = gerar_token(tipo, id_usuarios, 5)

        # Cria resposta com cookie
        resp = make_response(jsonify({'message': "Código correto! Você tem 5 minutos para alterar sua senha", 'token': token, 'id': id_usuarios}), 200)

        # Define cookie com token
        resp.set_cookie('acess_token', token,
                        httponly=True,
                        secure=False,
                        samesite='None',
                        path="/",
                        max_age=3600)

        return resp

    except Exception as e:
        return jsonify({'error': f'Erro: {e}'}), 500
    finally:
        cursor.close()
        con.close()


# Buscar dados do próprio usuário logado
@app.route('/meus_dados', methods=['GET'])
def meus_dados():
    token_data = decodificar_token()
    if token_data == False:
        return jsonify({'error': 'Token necessário'}), 401

    id_usuarios = token_data['id_usuarios']

    con = conexao()
    cur = con.cursor()

    try:
        cur.execute("""SELECT ID_USUARIOS, NOME, EMAIL, CPF_CNPJ, TELEFONE
                       FROM USUARIOS WHERE ID_USUARIOS = ?""", (id_usuarios,))
        usuario = cur.fetchone()

        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        return jsonify({
            'usuario': {
                'id': usuario[0],
                'nome': usuario[1],
                'email': usuario[2],
                'cpf_cnpj': usuario[3],
                'telefone': usuario[4]
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        con.close()
