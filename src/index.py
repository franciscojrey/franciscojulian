from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from functools import wraps
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.handlers.sha2_crypt import sha256_crypt
import pyodbc
import datetime
from datetime import date
import re
import itertools

# Configuración Flask
app = Flask(__name__)

# Conexión a la base de datos SQL Server
conx_string = "driver={SQL SERVER}; server=DESKTOP-97GRPND\SQLEXPRESS; database=ADACNSM; trusted_connection=YES;"

# Verifica que el usuario haya iniciado sesion
def verificar_loggeado(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'loggeado' in session:
			return f(*args, **kwargs)
		else:
			flash('Acceso no autorizado, por favor inicie sesión.', 'danger')
			return redirect(url_for('inicio_sesion'))
	return wrap

# Verifica que el usuario haya cerrado sesión
def verificar_no_loggeado(l):
	@wraps(l)
	def wrap(*args, **kwargs):
		if not 'loggeado' in session:
			return l(*args, **kwargs)
		# Chequear por qué cuando entro después de prender la pc me sale este cartel de abajo
		else:
			flash('Si desea dirigirse a esa página primero debe cerrar sesión', 'danger')
			return redirect(url_for('home'))
	return wrap

# Verifica que el usuario sea profesor
# Parametrizarlo para que verifique el tipo de usuario necesario
def es_profesor(g):
	@wraps(g)
	def wrap(*args, **kwargs):
		if 'profesor' in session:
			return g(*args, **kwargs)
		else:
			flash('Acceso no autorizado para su tipo de usuario.', 'danger')
			return redirect(url_for('home'))
	return wrap

@app.route('/')
def home():
	return render_template('home.html')

@app.route('/cerrar_sesion')
@verificar_loggeado
def cerrar_sesion():
	session.clear()
	flash('Has cerrado sesión.', 'success')
	return redirect(url_for('inicio_sesion'))

@app.route('/registro', methods=['GET', 'POST'])
#@verificar_no_loggeado
def registro():
	with pyodbc.connect(conx_string) as conx:
		cursor = conx.cursor()
		cursor.execute('EXEC SP_PerfilesRegistro')
		perfiles = cursor.fetchall()
	if request.method == 'POST':
		try:
			email = request.form['email']
			contraseña = request.form['contraseña']
			contraseña_repetida = request.form['contraseña_repetida']
			tipo_de_usuario = request.form['tipo_de_usuario']
			print(tipo_de_usuario)
			dni_formulario = request.form['dni']
			today = date.today()
			fecha_de_alta = today.strftime("%d/%m/%Y")
			# Chequeo del campo DNI
			dni_solo_numeros = True
			dni_formulario_ingresado = True
			campo_tipo_de_usuario_incorrecto = False
			dni_largo_correcto = True
			try:
				dni = int(dni_formulario)
				dni_formulario_fue_utilizado = False
				with pyodbc.connect(conx_string) as conx:
					cursor = conx.cursor()
					cursor.execute('EXEC SP_BuscaDniFormulario_Registro @dni = ?', dni)
					resultado_busca_dni = cursor.fetchone()
					if resultado_busca_dni:
						dni_formulario_fue_utilizado = True

				dni_formulario_existe = False
				# Hay que hacer stored procedures con los otros tipos de usuario
				try:
					cursor = conx.cursor()
					if tipo_de_usuario == "alumno":
						cursor.execute('EXEC SP_BuscaDniAlumno_Registro @dni = ?', dni)
					elif tipo_de_usuario == "profesor":
						cursor.execute('EXEC SP_BuscaDniDocente_Registro @dni = ?', dni)
					elif tipo_de_usuario == "preceptor":
						cursor.execute('EXEC SP_BuscaDniDocente_Registro @dni = ?', dni)
					elif tipo_de_usuario == "administrativo":
						cursor.execute('EXEC SP_BuscaDniDocente_Registro @dni = ?', dni)
					resultado_busca_dni = cursor.fetchone()
					if resultado_busca_dni[0] == dni:
						dni_formulario_existe = True		
				except TypeError:
					dni_formulario_existe = False	
				except pyodbc.ProgrammingError:
					campo_tipo_de_usuario_incorrecto = True
				
			except ValueError:
				if len(dni_formulario) == 0:
					dni_formulario_ingresado = False
				# Chequear que solo deje poner números con esto de abajo, no se si elimina todas las posibilidades
				else:
					dni_solo_numeros = False
			except OverflowError:
				dni_largo_correcto = False
			except pyodbc.ProgrammingError:
				dni_largo_correcto = False

			espacios_en_contraseña = 0
			for i in contraseña:
				if(i.isspace()):
					espacios_en_contraseña=espacios_en_contraseña+1
			
			espacios_en_email = 0
			for i in email:
				if(i.isspace()):
					espacios_en_email=espacios_en_email+1

			numeros_en_contraseña = 0
			for i in contraseña:
				if(i.isdigit()):
					numeros_en_contraseña=numeros_en_contraseña+1

			if email == "":
				flash('Debe ingresar una dirección de correo electrónico.', 'danger')
			elif email.count('@')!=1 or email.rfind('@')==(len(email)-1) or email.find('@')==0 or email.count('.')!=1 or email.rfind('.')==(len(email)-1) or email.find('.')==0 or espacios_en_email>0:
				flash('La dirección de correo ingresada no es correcta.', 'danger')
			elif len(email)<8 or len(email)>80:
				flash('La dirección de correo debe tener un mínimo de 8 carácteres y un máximo de 80.', 'danger')
			elif contraseña == "":
				flash('Debe ingresar una contraseña.', 'danger')
			elif len(contraseña)<8 or len(contraseña)>20:
				flash('La contraseña debe tener un mínimo de 8 carácteres y un máximo de 20.', 'danger')
			elif contraseña != contraseña_repetida:
				flash('Las contraseñas ingresadas no coinciden.', 'danger')
			elif len(re.findall(r'[A-Z]', contraseña))<1:
				flash('La contraseña debe tener como mínimo una letra mayúscula.', 'danger')
			elif len(re.findall(r'[a-z]', contraseña))<1:
				flash('La contraseña debe tener como mínimo una letra minúscula.', 'danger')
			elif espacios_en_contraseña>0:
				flash('La contraseña no puede contener espacios en blanco.', 'danger')
			elif numeros_en_contraseña<2:
				flash('La contraseña debe tener 2 o más números.', 'danger')
			# Ver si estos 2 de abajo no son repetitivos
			elif campo_tipo_de_usuario_incorrecto == True:
				flash('Debe especificar el tipo de usuario.', 'danger')
			elif tipo_de_usuario!="profesor" and tipo_de_usuario!="administrativo" and tipo_de_usuario!="preceptor" and tipo_de_usuario!="alumno":
				flash('El tipo de usuario ingresado no es válido.', 'danger')
			elif dni_formulario_ingresado == False:
				flash('Debe ingresar un DNI.', 'danger')
			elif dni_solo_numeros == False:
				flash('El DNI ingresado no es válido.', 'danger')
			elif dni_formulario_fue_utilizado == True:
				flash('Ya existe un usuario con el DNI ingresado.', 'danger')
			elif len(str(dni))<=6 or len(str(dni))>=9 or dni_largo_correcto == False:
				flash('El DNI debe tener entre 7 y 9 caracteres.', 'danger')
			# Hay que hacer que busque el dni de administrativos y preceptores también
			elif dni_formulario_existe == False:
				flash('El DNI ingresado no coincide con ningún registro de la base de datos.', 'danger')
			else:
				with pyodbc.connect(conx_string) as conx:
					contraseña = sha256_crypt.encrypt(str(contraseña)) 
					cursor = conx.cursor()
					cursor.execute('EXEC SP_RegistrarUsuario_Registro @email = ?, @contraseña = ?, @fecha_de_alta = ?, @tipo_de_usuario = ?, @dni = ?', (email, contraseña, fecha_de_alta, tipo_de_usuario, dni))
					flash('Su cuenta se ha registrado con éxito.', 'success')
		except pyodbc.IntegrityError:
			flash('Ya existe una cuenta con el email ingresado.', 'danger')
	return render_template('registro.html', perfiles = perfiles)

@app.route('/inicio_sesion', methods=['GET', 'POST'])
@verificar_no_loggeado
def inicio_sesion():
		if request.method == 'POST':
			email_formulario = request.form['email']
			contraseña = request.form['contraseña']
			if email_formulario == "" or contraseña == "":
				flash('Debe completar todos los campos.', 'danger')
			else:
				try: 
					with pyodbc.connect(conx_string) as conx:
						cursor = conx.cursor()
						cursor.execute('EXEC SP_BuscaDatosUsuario_InicioSesion @ema = ?', email_formulario)
						datos_usuario = cursor.fetchone()
					email_base_datos = datos_usuario[0]
					# ver si hace falta el str aca abajo
					tipo_de_usuario = str(datos_usuario[2])
					dni = datos_usuario[3]
					if email_base_datos == email_formulario:
						contraseña_base_datos = datos_usuario[1]
						# Comparo las contraseñas
						if sha256_crypt.verify(contraseña, contraseña_base_datos):
							session['loggeado'] = True
							session['email'] = email_base_datos
							session['dni'] = dni
							# Parametrizar para que sea con cualquier tipo de usuario
							if tipo_de_usuario == 'profesor':
								session['profesor'] = True
							elif tipo_de_usuario == 'alumno':
								session['alumno'] = True
							return redirect(url_for('home'))
						else:
							flash('La contraseña ingresada es incorrecta.', 'danger')
				except TypeError:
					flash('El email ingresado no es correcto o no existe. Por favor, revisalo e intenta nuevamente.', 'danger')
		return render_template('inicio_sesion.html')

@app.route('/posts')
@verificar_loggeado
def posts():
	try:
		with pyodbc.connect(conx_string) as conx:
			cursor = conx.cursor()
			cursor.execute('EXEC SP_VerPosts_Posts')
			posts = cursor.fetchall()
			if not posts:
				flash('Por el momento no hay publicaciones para mostrar.','warning')
			return render_template('posts.html', posts=posts)
	except TypeError:
		flash('No se encontraron publicaciones', 'warning')
		return render_template('posts.html')

# Ver un post en particular
@app.route('/ver_post/<string:id>/')
def ver_post(id):
	with pyodbc.connect(conx_string) as conx:
		cursor = conx.cursor()
		cursor.execute('EXEC SP_BuscaPost_VerPost @id = ?', id)
		post = cursor.fetchone()
		return render_template('ver_post.html', post=post)

@app.route('/administrar_posts')
@verificar_loggeado 
@es_profesor
def administrar_posts():
	try:
		with pyodbc.connect(conx_string) as conx:
			cursor = conx.cursor()
			cursor.execute('EXEC SP_VerPosts_AdministrarPosts')
			posts = cursor.fetchall()
			return render_template('administrar_posts.html', posts=posts)
	except TypeError:
		flash('No se encontraron tareas.', 'warning')
		return render_template('administrar_posts.html')

class ArticleForm(Form):
	titulo = StringField('Título')
	texto = TextAreaField('Texto')

def largoCaracteres(variable, nombreVariable, minimo, maximo):
	if len(variable)<minimo or len(variable)>maximo:
		return flash('El campo ' + nombreVariable + ' debe tener entre ' + str(minimo) + ' y ' + str(maximo) + ' caracteres','danger')

@app.route('/agregar_post', methods=['GET', 'POST'])
@verificar_loggeado
@es_profesor
def agregar_post():
	if request.method == 'POST':
		titulo = request.form['titulo']
		texto = request.form['texto']
		today = date.today()
		fecha_post = today.strftime("%d/%m/%Y")
		if texto == "" or titulo == "":
			flash('Debe completar todos los campos.', 'danger')	
		elif len(titulo)<5 or len(titulo)>60:
			flash('El titulo debe tener entre 5 y 60 caracteres.', 'danger')		
		elif len(texto)<30 or len(texto)>500:
			flash('El texto debe tener entre 30 y 500 caracteres.', 'danger')
		else:
			with pyodbc.connect(conx_string) as conx:
				cursor = conx.cursor()
				cursor.execute('EXEC SP_AgregarPost_AgregarPost @titulo = ?, @autor = ?, @texto = ?, @fecha_post = ?', (titulo,session['email'],texto,fecha_post))
				flash('Tarea creada.', 'success')
				return redirect(url_for('administrar_posts'))
	return render_template('agregar_post.html')

@app.route('/editar_post/<id>', methods=['GET', 'POST'])
@verificar_loggeado
@es_profesor
def edit(id):
	with pyodbc.connect(conx_string) as conx:
		cursor = conx.cursor()
		cursor.execute('EXEC SP_BuscarPost_EditarPost @id = ?', id)
		post = cursor.fetchone()
	form = ArticleForm(request.form)
	form.titulo.data = post[0]
	form.texto.data = post[1]
	if request.method == 'POST':
		titulo = request.form['titulo']
		texto = request.form['texto']
		if texto == "" or titulo == "":
			flash('Debe completar todos los campos.', 'danger')
		elif len(titulo)<5 or len(titulo)>60:
			flash('El titulo debe tener entre 5 y 60 caracteres.', 'danger')		
		elif len(texto)<30 or len(texto)>500:
			flash('El texto debe tener entre 30 y 500 caracteres.', 'danger')
		else:
			with pyodbc.connect(conx_string) as conx:
				cursor = conx.cursor()
				cursor.execute('EXEC SP_EditarPost_EditarPost @titulo = ?, @texto = ?, @id = ?', (titulo,texto,id))
			flash('Tarea editada correctamente.', 'success')
			return redirect(url_for('administrar_posts'))
		form.titulo.data = titulo
		form.texto.data = texto
	return render_template('editar_post.html', form=form)

@app.route('/eliminar_post/<string:id>', methods=['POST'])
@verificar_loggeado
@es_profesor
def eliminar_post(id):
	with pyodbc.connect(conx_string) as conx:
		cursor = conx.cursor()
		cursor.execute('EXEC SP_EliminarPost_EliminarPost @id = ?', id)
	flash('Tarea eliminada correctamente.', 'success')
	return redirect(url_for('administrar_posts'))

@app.route('/cargar_notas', methods=['POST', 'GET'])
@verificar_loggeado
@es_profesor
def cargar_notas():
	# Chequear que esto esté bien hecho después de haber hecho todo en un solo stored procedure
	with pyodbc.connect(conx_string) as conx:
		fecha = datetime.datetime.now()
		anio = fecha.year #Cuando esté todo listo hay que poner la variable '@anio' en vez de 2019 en SP_PlanillaAlumnosNotas
		cursor = conx.cursor()
		cursor.execute('EXEC SP_BuscaMateriaDocente @dni = ?', session['dni'])
		materias = cursor.fetchall()
		if request.method == 'POST':
			try:
				cursor = conx.cursor()	
				materia_anr = request.form['materia']
				cursor.execute('SP_PlanillaAlumnosNotas @anr = ?', materia_anr)
				planilla_alumnos_notas = cursor.fetchall()
				return render_template('cargar_notas.html', materias = materias, planilla_alumnos_notas = planilla_alumnos_notas)
			except TypeError:
				flash('Debe seleccionar una materia.','danger')
	return render_template('cargar_notas.html', materias = materias)

@app.route('/ver_notas')
def ver_notas():
	if session['alumno'] == True:
		with pyodbc.connect(conx_string) as conx:
			cursor = conx.cursor()
			cursor.execute('EXEC SP_BuscaNotasAlumno @dni = ?', session['dni'])
			notas_materias = cursor.fetchall()
	return render_template('ver_notas.html', notas_materias = notas_materias)


@app.route('/actualizar_notas', methods=['POST'])
@verificar_loggeado
@es_profesor
def actualizar_notas():
	if request.method == 'POST':
		nota1 = request.form.getlist('NOTA1')
		nota2 = request.form.getlist('NOTA2')
		nota3 = request.form.getlist('NOTA3')
		alumno = request.form.getlist('ALU')
		materia = request.form.getlist('materia')
	notas_ingresadas_validas = True
	campo_notas_vacio = False
	caracter_invalido = False
	# Une las listas 
	for x in itertools.chain(nota1, nota2, nota3):
		try:
			float(x)
			if x == "":
				campo_notas_vacio = True
			# Chequea que las notas estén entre 1 y 10
			elif float(x)<1 or float(x)>10:
				notas_ingresadas_validas = False
		except ValueError:
			caracter_invalido = True

	if campo_notas_vacio:
		flash('No puede haber campos vacíos.','danger')
	elif caracter_invalido:
		flash('Solamente pueden ingresarse números enteros o decimales.','danger')
	elif notas_ingresadas_validas == False:
		flash('Los valores ingresados en uno o más campos son incorrectos. La nota ingresada no puede ser menor a 1 o mayor a 10.','danger')
	else:
		# Intercala las listas
		notas_lista = list(itertools.chain.from_iterable(zip(nota1, nota2, nota3, alumno, materia)))
		try:
			[float(i) for i in notas_lista]
			# Separa en bloques de 5 los elementos de las listas
			lista_notas = [notas_lista[i:i + 5] for i in range (0, len(notas_lista), 5)]
			with pyodbc.connect(conx_string) as conx:
				cursor = conx.cursor()
				act_notas = """ UPDATE [CURXALUM] 
								SET [CURXALUM].[NOTA1] = ?, [CURXALUM].[NOTA2] = ?, [CURXALUM].[NOTA3] = ? 
								WHERE [CURXALUM].[ALU] = ? AND [CURXALUM].[MAT] = ?"""
				# Ver cómo hacer un Stored Procedure para que ejecute una lista
				#cursor.execute('EXEC SP_ActualizarNotas_ActualizarNotas @nota1 = ?, @nota2 = ?, @nota3 = ?, @alu = ?', (lista_notas))
				cursor.executemany(act_notas, lista_notas)  
			flash('Notas actualizadas correctamente.', 'success')   
			return redirect(url_for('cargar_notas'))   
		except ValueError:
			flash('Carácter no válido en uno de los campos. Revise las notas ingresadas e intente nuevamente.', 'danger')   
	return redirect(url_for('cargar_notas'))  

@app.route('/cuenta', methods=['GET', 'POST'])
def cuenta():
	return render_template('cuenta.html')

@app.route('/cambiar_contraseña', methods=['GET', 'POST'])
def cambiar_contraseña():
	return render_template('cambiar_contraseña.html')

class PerfilFormulario(Form):
	codigo_formulario = StringField('Código')
	nombre = StringField('Nombre')
	nombre_completo = StringField('Nombre completo')

@app.route('/administrar_perfiles', methods=['GET', 'POST'])
def administrar_perfiles():
	try:
		with pyodbc.connect(conx_string) as conx:
			cursor = conx.cursor()
			cursor.execute('EXEC SP_VerPerfiles')
			perfiles = cursor.fetchall()
			return render_template('administrar_perfiles.html', perfiles=perfiles)
	except TypeError:
		flash('No se encontraron perfiles.', 'warning')
		return render_template('administrar_perfiles.html')
	
@app.route('/agregar_perfil', methods=['GET', 'POST'])
def agregar_perfil():
	if request.method == 'POST':
		codigo_perfil = request.form['codigo_perfil']
		nombre_perfil = request.form['nombre_perfil']
		nombre_completo_perfil = request.form['nombre_completo_perfil']
		with pyodbc.connect(conx_string) as conx:
			cursor = conx.cursor()
			cursor.execute('EXEC SP_AgregarPerfil @codigo = ?, @nombre = ?, @nombre_completo = ?', (codigo_perfil, nombre_perfil, nombre_completo_perfil))
		flash('Tarea creada correctamente.', 'success')
		return redirect(url_for('administrar_perfiles'))
	return render_template('agregar_perfil.html')

@app.route('/editar_perfil/<codigo>', methods=['GET', 'POST'])
def editar_perfil(codigo):
	with pyodbc.connect(conx_string) as conx:
		cursor = conx.cursor()
		cursor.execute('EXEC SP_VerPerfilAEditar @codigo = ?', codigo)
		perfil = cursor.fetchone()
	form = PerfilFormulario(request.form)
	form.codigo_formulario.data = perfil[0]
	form.nombre.data = perfil[1]
	form.nombre_completo.data = perfil[1]
	if request.method == 'POST':
		codigo_formulario = request.form['codigo_formulario']
		nombre = request.form['nombre']
		nombre_completo = request.form['nombre_completo']
		with pyodbc.connect(conx_string) as conx:
			cursor = conx.cursor()
			cursor.execute('EXEC SP_EditarPerfil @codigo_formulario = ?, @nombre = ?, @nombre_completo = ?, @codigo=?', (codigo_formulario,nombre,nombre_completo, codigo))
		flash('Perfil editado correctamente.', 'success')
		return redirect(url_for('administrar_perfiles'))
		# Agregar esto cuando agregue las validaciones y haya errores, para que no se borren los cambios ingresados
		#form.codigo.data = codigo
		#form.nombre.data = nombre
	return render_template('editar_perfil.html', form=form)

@app.route('/eliminar_perfil/<string:codigo>', methods=['POST'])
def eliminar_perfil(codigo):
	with pyodbc.connect(conx_string) as conx:
		cursor = conx.cursor()
		cursor.execute('EXEC SP_EliminarPerfil @codigo = ?', codigo)
	flash('Perfil eliminado correctamente.', 'success')
	return redirect(url_for('administrar_perfiles'))

@app.route('/usuarios_perfiles')
def usuarios_perfiles():
	return render_template('usuarios_perfiles.html')

if __name__ == '__main__':
	app.secret_key='secret123'
	app.run(debug=True)