# -*- coding: utf-8 -*-
from django.http import Http404, HttpResponse
from django.template.defaultfilters import slugify
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404
from django.views.generic.simple import direct_to_template
from django.utils import simplejson
from django.db.models import Sum, Count, Avg
from django.core.exceptions import ViewDoesNotExist
from decorators import session_required
from datetime import date
from forms import *
from decimal import Decimal

from monitoreo.encuestas.models import *
from monitoreo.agroecologico.models import *
from monitoreo.animales.models import *
from monitoreo.bienes.models import *
from monitoreo.comercializacion.models import *
from monitoreo.cultivos.models import *
from monitoreo.estado.models import *
from monitoreo.familias.models import *
from monitoreo.genero.models import *
from monitoreo.ingreso.models import *
from monitoreo.organizacion.models import *
from monitoreo.otrosIngresos.models import *
from monitoreo.reforestacion.models import *
from monitoreo.riesgos.models import *
from monitoreo.seguridad.models import *
from monitoreo.suelo.models import *
from monitoreo.tierra.models import *
from monitoreo.lugar.models import *


from utils import grafos
from utils import *

# Create your views here.

def _get_view(request, vista):
    if vista in VALID_VIEWS:
        return VALID_VIEWS[vista](request)
    else:
        raise ViewDoesNotExist("Tried %s in module %s Error: View not defined in VALID_VIEWS." % (vista, 'encuestas.views'))
        
#-------------------------------------------------------------------------------
        
def _queryset_filtrado(request):
    '''metodo para obtener el queryset de encuesta 
    segun los filtros del formulario que son pasados
    por la variable de sesion'''
    #anio = int(request.session['fecha'])
    #diccionario de parametros del queryset
    params = {}
    if 'fecha' in request.session:
        params['year__in'] = request.session['fecha']
        
    if request.session['departamento']:
        if not request.session['municipio']:
            municipios = Municipio.objects.filter(departamento__in=request.session['departamento'])
            params['municipio__in'] = municipios
        else:
            if request.session['comunidad']:
                params['comunidad__in'] = request.session['comunidad']
            else:
                params['municipio__in'] = request.session['municipio']
            
#    if request.session['organizacion']:
#        params['organizacion__in'] = request.session['organizacion']

#        if 'departamento' in request.session:
#            #incluye municipio y comunidad
#            if request.session['municipio']:                
#                if 'comunidad' in request.session and request.session['comunidad'] != None:
#                    params['comunidad'] = request.session['comunidad']                    
#                else:
#                    params['comunidad__municipio'] = request.session['municipio']                                        
#            else:
#                params['comunidad__municipio__departamento'] = request.session['departamento']

    if 'sexo' in  request.session:
        params['sexo'] = request.session['sexo']
        
    if 'organizacion' in request.session:
        params['beneficiario__in'] = request.session['organizacion']

    if 'grupo' in  request.session:
        params['grupo__in'] = request.session['grupo']            

    if 'duenio' in  request.session:
        params['tenencia__dueno'] = request.session['duenio']
    
    unvalid_keys = []
    for key in params:
        if not params[key]:
            unvalid_keys.append(key)
    
    for key in unvalid_keys:
        del params[key]
    
    return Encuesta.objects.filter(**params)

#-------------------------------------------------------------------------------

# Comienza la parte del index

def inicio(request): 
    if request.method == 'POST':
        mensaje = None
        form = MonitoreoForm(request.POST)
        if form.is_valid():
            request.session['fecha'] = form.cleaned_data['fecha']
            request.session['departamento'] = form.cleaned_data['departamento']
            request.session['organizacion'] = form.cleaned_data['organizacion']
            request.session['municipio'] = form.cleaned_data['municipio']
            request.session['comunidad'] = form.cleaned_data['comunidad']            
#            request.session['organizacion'] = form.cleaned_data['organizacion']
#            request.session['fecha'] = form.cleaned_data['fecha']
#            request.session['departamento'] = form.cleaned_data['departamento']
#            try:
#                municipio = Municipio.objects.get(id=int(form.cleaned_data['municipio'])) 
#            except:
#                municipio = None
#            try:
#                comunidad = Comunidad.objects.get(id=int(form.cleaned_data['comunidad']))                
#            except:
#                comunidad = None

#            request.session['municipio'] = municipio 
#            request.session['comunidad'] = comunidad
            request.session['grupo'] = form.cleaned_data['grupo']
            request.session['sexo'] = form.cleaned_data['sexo']
            request.session['duenio'] = form.cleaned_data['dueno']

            mensaje = "Todas las variables estan correctamente :)"
            request.session['activo'] = True
            centinela = 1
        else:
            centinela = 0            
    else:
        form = MonitoreoForm()
        mensaje = "Existen alguno errores"
        centinela = 0
    
    shva = request.GET.get('shva', '')
    if shva and request.session['activo']:
        shva = 1
        centinela = 1
    
    dict = {'form': form,'user': request.user,'centinela':centinela, 'shva':shva}
    return render_to_response('encuestas/inicio.html', dict,
                              context_instance=RequestContext(request))        
        
#-------------------------------------------------------------------------------
def index(request):
    familias = Encuesta.objects.all().count()
    #organizacion = OrganizacionesOCB.objects.all().count()  

    return direct_to_template(request, 'index.html', locals())        

def proyecto(request):
    return direct_to_template(request, 'proyecto.html', locals())        
        
#-------------------------------------------------------------------------------
def generales(request):
    numero = Encuesta.objects.all().count()
    
    mujeres = Encuesta.objects.filter(sexo=2).count()
    por_mujeres = round(saca_porcentajes(mujeres,numero),2)
    hombres = Encuesta.objects.filter(sexo=1).count()
    por_hombres = round(saca_porcentajes(hombres,numero),2)  
    
    #Educacion
    escolaridad = []
    valores_e = []
    leyenda_e = []
    for escuela in CHOICE_EDUCACION:
        conteo = Encuesta.objects.filter(educacion__sexo=escuela[0]).aggregate(conteo=Count('educacion__sexo'))['conteo']
        porcentaje = round(saca_porcentajes(conteo,numero),2)
        escolaridad.append([escuela[1],conteo,porcentaje])
        valores_e.append(conteo)
        leyenda_e.append(escuela[1])
        
    grafo_url = grafos.make_graph(valores_e, leyenda_e, 'Tipos de escolaridad', return_json=False ,type=grafos.PIE_CHART_2D)
        
        
    #Departamentos   
    depart = []
    valores_d = []
    leyenda_d = []  
    for depar in Departamento.objects.all():
        conteo = Encuesta.objects.filter(comunidad__municipio__departamento=depar).aggregate(conteo=Count('comunidad__municipio__departamento'))['conteo']
        porcentaje = round(saca_porcentajes(conteo,numero))
        if conteo != 0:
            depart.append([depar.nombre,conteo,porcentaje])
            valores_d.append(conteo)
            leyenda_d.append(depar.nombre)
            
    grafo_depart = grafos.make_graph(valores_d, leyenda_d, 'Departamentos Encuestados', return_json=False ,type=grafos.PIE_CHART_2D)

    #Municipios        
    munis = []
    valores_m = []
    leyenda_m = []
    for mun in Municipio.objects.all():
        conteo = Encuesta.objects.filter(comunidad__municipio=mun).aggregate(conteo=Count('comunidad__municipio'))['conteo']
        porcentaje = round(saca_porcentajes(conteo,numero))
        if conteo != 0:
            munis.append([mun.nombre,conteo,porcentaje])
            valores_m.append(conteo)
            leyenda_m.append(mun.nombre)
      
    grafo_munis = grafos.make_graph(valores_m, leyenda_m, 'Municipios Encuestados', return_json=False ,type=grafos.PIE_CHART_2D)
            
    #salidas de grupos etnicos
    grupo = []
    for etnico in CHOICE_ETNICO:
        conteo = Encuesta.objects.filter(grupo=etnico[0]).count()
        porcentaje = round(saca_porcentajes(conteo,numero))
        grupo.append([etnico[1],conteo,porcentaje])

    return render_to_response('encuestas/generales.html', locals(),
                               context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#Tabla Educación
@session_required
def educacion(request):
    '''Tabla de educacion 
    '''
    #*******Variables globales**********
    a = _queryset_filtrado(request)
    num_familias = a.count()
    #**********************************
    
    tabla_educacion = []
    grafo = []
    suma = 0 
    for e in CHOICE_EDUCACION:
        objeto = a.filter(educacion__sexo = e[0]).aggregate(num_total = Sum('educacion__total'),
                no_leer = Sum('educacion__no_leer'), 
                p_incompleta = Sum('educacion__p_incompleta'), 
                p_completa = Sum('educacion__p_completa'), 
                s_incompleta = Sum('educacion__s_incompleta'),
                bachiller = Sum('educacion__bachiller'), 
                universitario = Sum('educacion__universitario'),
                f_comunidad = Sum('educacion__f_comunidad'))
        try:
            suma = int(objeto['p_completa'] or 0) + int(objeto['s_incompleta'] or 0) + int(objeto['bachiller'] or 0) + int(objeto['universitario'] or 0)
        except:
            pass
        variable = round(saca_porcentajes(suma,objeto['num_total']))
        grafo.append([e[1],variable])
        
        fila = [e[1], objeto['num_total'],
                saca_porcentajes(objeto['no_leer'], objeto['num_total'], False),
                saca_porcentajes(objeto['p_incompleta'], objeto['num_total'], False),
                saca_porcentajes(objeto['p_completa'], objeto['num_total'], False),
                saca_porcentajes(objeto['s_incompleta'], objeto['num_total'], False),
                saca_porcentajes(objeto['bachiller'], objeto['num_total'], False),
                saca_porcentajes(objeto['universitario'], objeto['num_total'], False),
                saca_porcentajes(objeto['f_comunidad'], objeto['num_total'], False)]
        tabla_educacion.append(fila)
    
    return render_to_response('familias/educacion.html', {'tabla_educacion':tabla_educacion,
                                  'num_familias':num_familias,'grafo':grafo},
                                  context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#Tabla Energia
@session_required
def luz(request):
    '''Tabla de acceso a energia electrica'''
    consulta = _queryset_filtrado(request)
    tabla = []
    total_tiene_luz = 0            

    for choice in PreguntaEnergia.objects.exclude(id=2):
        query = consulta.filter(energia__pregunta=choice, energia__respuesta=1).distinct()
        resultados = query.count() 
        if choice.pregunta == 1:
            total_tiene_luz = resultados 
            fila = [choice.pregunta, 
                    resultados,
                    saca_porcentajes(resultados, consulta.count(), False)]
            tabla.append(fila)
        else:
            fila = [choice.pregunta, 
                    resultados,
                    saca_porcentajes(resultados, consulta.count(), False)]
            tabla.append(fila)
    tabla_cocina = []        
    for cocina in TipoCocina.objects.all():
        conteo = consulta.filter(cocina__utiliza=cocina).count()
        porcentaje = round(saca_porcentajes(conteo,consulta.count()))
        tabla_cocina.append([cocina.nombre,conteo,porcentaje])
        
    return render_to_response('familias/luz.html', 
                              {'tabla':tabla, 'num_familias': consulta.count(),
                               'tabla_cocina':tabla_cocina},
                              context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#Tabla Agua
@session_required
def agua(request):
    '''Agua'''
    consulta = _queryset_filtrado(request)
    tabla = []
    total = consulta.aggregate(total=Count('agua__fuente'))

    for choice in Fuente.objects.all():
        query = consulta.filter(agua__fuente=choice)
        numero = query.count()
        fila = [choice.nombre, numero,
                #saca_porcentajes(numero, total['total'], False),
                saca_porcentajes(numero, consulta.count(), False)
                ]
        tabla.append(fila)

    #totales = [total['total'], 100, total['cantidad'], 100]
    totales = [consulta.count(), 100]
    return render_to_response('familias/agua.html', 
                              #{'tabla':tabla, 'totales':totales},
                              {'tabla':tabla, 'num_familias': consulta.count()},
                              context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#GRAFICOS
@session_required
def organizacion_grafos(request, tipo):
    '''grafos de organizacion
       tipo puede ser: beneficio, miembro'''
    consulta = _queryset_filtrado(request)
    
    data = [] 
    legends = []
    if tipo == 'beneficio':
        for opcion in BeneficiosObtenido.objects.all():
            data.append(consulta.filter(organizaciongremial__beneficio=opcion).count())
            legends.append(opcion.nombre)
        return grafos.make_graph(data, legends, 
                'Beneficios obtenidos siendo socio/a de la cooperativa, la asociación o empresa', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'miembro':
        for opcion in SerMiembro.objects.all():
            data.append(consulta.filter(organizaciongremial__beneficio=opcion).count())
            legends.append(opcion.nombre)
        return grafos.make_graph(data, legends, 
                'Porque soy o quiero ser miembro de la junta directiva o las comisiones', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'estructura':
        for opcion in CHOICE_OPCION:
            data.append(consulta.filter(organizaciongremial__asumir_cargo=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends, 
                'Si no es miembro de ninguna estructura ¿estaria interesado en asumir cargos?', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'beneficiorganizado':
        for opcion in BeneficioOrgComunitaria.objects.all():
            data.append(consulta.filter(organizacioncomunitaria__cual_beneficio=opcion).count())
            legends.append(opcion.nombre)
        return grafos.make_graph(data, legends, 
                '¿Cuáles son los beneficios de estar organizado', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'norganizado':
        for opcion in NoOrganizado.objects.all():
            data.append(consulta.filter(organizacioncomunitaria__no_organizado=opcion).count())
            legends.append(opcion.nombre)
        return grafos.make_graph(data, legends, 
                '¿Porqué no esta organizado?', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'comunitario':
        for opcion in OrgComunitarias.objects.all():
            data.append(consulta.filter(organizacioncomunitaria__cual_organizacion=opcion).count())
            legends.append(opcion.nombre)
        return grafos.make_graph(data, legends, 
                '¿A cual organizacion comunitaria pertenece', return_json = True,
                type = grafos.PIE_CHART_2D)
    else:
        raise Http404
            
@session_required
def agua_grafos_disponibilidad(request, tipo):
    '''Tipo: numero del 1 al 6 en CHOICE_FUENTE_AGUA'''
    consulta = _queryset_filtrado(request)
    data = [] 
    legends = []
    tipo = get_object_or_404(Fuente, id = int(tipo)) 
    for opcion in Disponibilidad.objects.all():
        data.append(consulta.filter(agua__disponible=opcion, agua__fuente = tipo).count())
        legends.append(opcion.nombre)
    titulo = 'Disponibilidad del agua en %s' % tipo.nombre 
    return grafos.make_graph(data, legends, 
            titulo, return_json = True,
            type = grafos.PIE_CHART_2D)
            
@session_required
def fincas_grafos(request, tipo):
    '''Tipo puede ser: tenencia, solares, propietario'''
    consulta = _queryset_filtrado(request)
    #CHOICE_TENENCIA, CHOICE_DUENO
    data = [] 
    legends = []
    if tipo == 'tenencia':
        for opcion in CHOICE_TENENCIA:
            data.append(consulta.filter(tenencia__parcela=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends, 
                'Tenencia de las parcelas', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'solares':
        for opcion in CHOICE_TENENCIA:
            data.append(consulta.filter(tenencia__solar=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends, 
                'Tenencia de los solares', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'propietario':
        for opcion in CHOICE_DUENO:
            data.append(consulta.filter(tenencia__dueno=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends, 
                'Dueño de propiedad', return_json = True,
                type = grafos.PIE_CHART_2D)
    else:
        raise Http404 
        
@session_required
def grafo_manejosuelo(request, tipo):
    #--- variables ---
    consulta = _queryset_filtrado(request)
    data = [] 
    legends = []
    #-----------------
    if tipo == 'analisis':
        for opcion in CHOICE_OPCION:
            data.append(consulta.filter(manejosuelo__analisis=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends, 
                '¿Realiza análisis de fertilidad del suelo', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'practica':
        for opcion in CHOICE_OPCION:
            data.append(consulta.filter(manejosuelo__practica=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends,
                                 '¿Realiza práctica de conservación de suelo', return_json=True,
                                 type = grafos.PIE_CHART_2D)
    else:
        raise Http404
    

@session_required
def grafos_ingreso(request, tipo):
    ''' tabla sobre los ingresos familiares
    '''
    #------ varaibles ------
    consulta = _queryset_filtrado(request)
    data = []
    legends = []
    #-----------------------
    if tipo == 'vendio':
        for opcion in CHOICE_VENDIO:
            data.append(consulta.filter(ingresofamiliar__quien_vendio=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends,
                'A quien venden', return_json=True,
                type=grafos.PIE_CHART_2D)
    elif tipo == 'maneja':
        for opcion in CHOICE_MANEJA:
            data.append(consulta.filter(ingresofamiliar__maneja_negocio=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends,
                'Quien maneja negocio', return_json=True,
                type=grafos.PIE_CHART_2D)
    elif tipo == 'ingreso':
        for opcion in CHOICE_MANEJA:
            data.append(consulta.filter(otrosingresos__tiene_ingreso=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends,
                'Quien tiene los ingresos', return_json=True,
                type=grafos.PIE_CHART_2D)
    elif tipo == 'salario':
        for opcion in TipoTrabajo.objects.all()[:4]:
            data.append(consulta.filter(otrosingresos__fuente__nombre__icontains="Salarios",
                                        otrosingresos__tipo=opcion).count())
            legends.append(opcion)
        return grafos.make_graph(data, legends,
                'Tipos de salarios', return_json=True,
                type=grafos.PIE_CHART_2D)
    elif tipo == 'negocio':
        for opcion in TipoTrabajo.objects.all()[4:8]:
            data.append(consulta.filter(otrosingresos__fuente__nombre__icontains="Negocios",
                                        otrosingresos__tipo=opcion).count())
            legends.append(opcion)
        return grafos.make_graph(data, legends,
                'Tipos de Negocios', return_json=True,
                type=grafos.PIE_CHART_2D)
    elif tipo == 'remesa':
        #for opcion in TipoTrabajo.objects.all()[9:9]:
        nacional = consulta.filter(otrosingresos__fuente__nombre__icontains="Remesas").count()
        extran = consulta.filter(otrosingresos__fuente__nombre__icontains="Remesas",
                                    otrosingresos__tipo=9).count()
        data = (nacional,extran)
        legends = ('Nacional','Extranjero')
        return grafos.make_graph(data, legends,
                'Tipos de Remesas', return_json=True,
                type=grafos.PIE_CHART_2D)
    elif tipo == 'alquiler':
        for opcion in TipoTrabajo.objects.all():
            data.append(consulta.filter(otrosingresos__fuente__nombre__icontains="Alquiler",
                                        otrosingresos__tipo=opcion).count())
            legends.append(opcion)
        return grafos.make_graph(data, legends,
                'Tipos de Alquiler', return_json=True,
                type=grafos.PIE_CHART_2D)
    else:
        raise Http404
        
@session_required
def grafos_bienes(request, tipo):
    '''tabla de bienes'''
    #----- variables ------
    consulta = _queryset_filtrado(request)
    data = [] 
    legends = []
    #----------------------
    if tipo == 'tipocasa':
        for opcion in Casa.objects.all():
            data.append(consulta.filter(tipocasa__tipo=opcion).count())
            legends.append(opcion.nombre)
        return grafos.make_graph(data, legends, 
                'Tipos de casas', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'tipopiso': 
        for opcion in Piso.objects.all():
            data.append(consulta.filter(tipocasa__piso=opcion).count())
            legends.append(opcion.nombre)
        return grafos.make_graph(data, legends, 
                'Tipo de pisos', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'tipotecho':
        for opcion in Techo.objects.all():
            data.append(consulta.filter(tipocasa__techo=opcion).count())
            legends.append(opcion.nombre)
        return grafos.make_graph(data, legends, 
                'Tipos de Techos', return_json = True,
                type = grafos.PIE_CHART_2D)
    elif tipo == 'ambiente':
        for opcion in CHOICE_AMBIENTE:
            data.append(consulta.filter(detallecasa__ambientes=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends,
               'Numeros de ambientes', return_json = True,
               type = grafos.PIE_CHART_2D)
    elif tipo == 'letrina':
        for opcion in CHOICE_OPCION[:2]:
            data.append(consulta.filter(detallecasa__letrina=opcion[0]).count())
            legends.append(opcion[1])
        return grafos.make_graph(data, legends,
                'Tiene letrina', return_json = True,
                type = grafos.PIE_CHART_2D)
#    elif tipo == 'lavadero':
#        for opcion in CHOICE_OPCION:
#            data.append(consulta.filter(detallecasa__lavadero=opcion[0]).count())
#            legends.append(opcion[1])
#        return grafos.make_graph(data, legends,
#               'Tiene lavadero', return_json = True,
#               type = grafos.PIE_CHART_2D)
            
    else:
        raise Http404
            
#Tabla Organizacion Gremial
@session_required
def gremial(request):
    '''tabla de organizacion gremial'''
     #***********Variables***************
    a = _queryset_filtrado(request)
    num_familias = a.count()
    #***********************************
    
    tabla_gremial = {}
    divisor = a.aggregate(divisor=Count('organizaciongremial__socio'))['divisor']
    ninguno = (num_familias - divisor) + a.filter(organizaciongremial__socio=5).count()
    por_ninguno = saca_porcentajes(ninguno,num_familias)
    
    for i in OrgGremiales.objects.exclude(id=5):
        key = slugify(i.nombre).replace('-', '_')
        query = a.filter(organizaciongremial__socio = i)
        frecuencia = query.aggregate(frecuencia=Count('organizaciongremial__socio'))['frecuencia']     
        porcentaje = saca_porcentajes(frecuencia,num_familias)
        tabla_gremial[key] = {'frecuencia':frecuencia, 'porcentaje':porcentaje}
    tabla_gremial['ninguno'] = {'frecuencia':ninguno, 'porcentaje':por_ninguno}

    #desde gremial
    tabla_desde = {}
    divisor1 = a.exclude(organizaciongremial__desde_socio=3).aggregate(divisor1=Count('organizaciongremial__desde_socio'))['divisor1']    
    for k in CHOICE_DESDE[:2]:
        key = slugify(k[1]).replace('-','_')
        query = a.filter(organizaciongremial__desde_socio = k[0])
        frecuencia = query.aggregate(frecuencia=Count('organizaciongremial__desde_socio'))['frecuencia']
        porcentaje = saca_porcentajes(frecuencia,divisor1)
        tabla_desde[key] = {'frecuencia':frecuencia, 'porcentaje':porcentaje}
     
    #miembro
    tabla_miembro = {}
    divisor2  = a.filter(organizaciongremial__miembro_gremial__in=(1,2,3)).count()
    no_miembro = (num_familias - divisor2) + a.filter(organizaciongremial__miembro_gremial=2).count()
    por_no_miembro = saca_porcentajes(no_miembro,num_familias)
                                         
    for p in CHOICE_MIEMBRO_GREMIAL[::2]:
        key = slugify(p[1]).replace('-','_')
        query = a.filter(organizaciongremial__miembro_gremial = p[0])
        frecuencia = query.aggregate(frecuencia=Count('organizaciongremial__miembro_gremial'))['frecuencia']
        porcentaje = saca_porcentajes(frecuencia,num_familias)
        tabla_miembro[key] = {'frecuencia':frecuencia, 'porcentaje':porcentaje}
    tabla_miembro['no'] = {'frecuencia':no_miembro,'porcentaje':por_no_miembro}
        
    #capacitación
    tabla_capacitacion = {}
    divisor4 = a.filter(organizaciongremial__capacitacion__in=[1,2]).count()
    no_capasitacion = (num_familias - divisor4) + a.filter(organizaciongremial__capacitacion=2).count()
    por_no_capasitacion = saca_porcentajes(no_capasitacion,num_familias)
        
    for t in CHOICE_OPCION[:1]:
        key = slugify(t[1]).replace('-','_')
        query = a.filter(organizaciongremial__capacitacion = t[0])
        frecuencia = query.aggregate(frecuencia=Count('organizaciongremial__capacitacion'))['frecuencia']
        porcentaje = saca_porcentajes(frecuencia,num_familias)
        tabla_capacitacion[key] = {'frecuencia':frecuencia, 'porcentaje':porcentaje}
    tabla_capacitacion['no'] = {'frecuencia':no_capasitacion,'porcentaje':por_no_capasitacion}        
        
    return render_to_response('organizacion/gremial.html', 
                                 {'tabla_gremial': tabla_gremial, 'tabla_desde':tabla_desde,
                                 'num_familias': num_familias,'divisor':divisor,'divisor1':divisor1,
                                 'tabla_miembro':tabla_miembro, 'divisor2':divisor2,
                                 
                                 'tabla_capacitacion':tabla_capacitacion, 'divisor4':divisor4},
                                 context_instance=RequestContext(request))
                                 
#-------------------------------------------------------------------------------
#Tabla Organizacion comunitaria
@session_required
def comunitario(request):
    ''' tablas organización comunitaria '''
    #***********Variables***************
    a = _queryset_filtrado(request)
    num_familias = a.count()
    #***********************************
    
    #rangos
    uno = a.filter(organizacioncomunitaria__numero__range=(1,5)).count()
    dos = a.filter(organizacioncomunitaria__numero__range=(6,10)).count()
    tres = a.filter(organizacioncomunitaria__numero__gt=11).count()
    
    tabla_pertenece = {}
    divisor = a.filter(organizacioncomunitaria__pertence__in=[1,2]).count()    
    for t in CHOICE_OPCION[:2]:
        key = slugify(t[1]).replace('-','_')
        query = a.filter(organizacioncomunitaria__pertence = t[0])
        frecuencia = query.aggregate(frecuencia=Count('organizacioncomunitaria__pertence'))['frecuencia']
        porcentaje = saca_porcentajes(frecuencia,divisor)
        tabla_pertenece[key] = {'frecuencia':frecuencia, 'porcentaje':porcentaje}    
    
    
        
    return render_to_response('organizacion/comunitario.html', {'tabla_pertenece':tabla_pertenece, 
                              'divisor':divisor, 'num_familias': num_familias,
                              'uno':uno,'dos':dos,'tres':tres},
                                context_instance=RequestContext(request) )
#-------------------------------------------------------------------------------
                          #aca van grafos de tenencia                       
#Tabla Uso Tierra
@session_required
def fincas(request):
    '''Tabla de fincas'''

    tabla = {}
    totales = {}
    consulta = _queryset_filtrado(request)
    num_familias = consulta.count()
    
    suma = 0
    total_manzana = 0
    por_num = 0
    por_man = 0
    
    for total in Uso.objects.exclude(id=1):
        conteo = consulta.filter(usotierra__tierra = total)
        suma += conteo.count()
        man = conteo.aggregate(area = Sum('usotierra__area'))['area']
        try:
            total_manzana += man
        except:
            total_manzana = 0
    
    totales['numero'] = suma
    totales['manzanas'] = round(total_manzana,0)
    totales['promedio_manzana'] = round(totales['manzanas'] / consulta.count(),2)

    for uso in Uso.objects.exclude(id=1):
        key = slugify(uso.nombre).replace('-', '_')
        query = consulta.filter(usotierra__tierra = uso)
        numero = query.count()
        porcentaje_num = saca_porcentajes(numero, num_familias)
        por_num += porcentaje_num
        manzanas = query.aggregate(area = Sum('usotierra__area'))['area']
        porcentaje_mz = saca_porcentajes(manzanas, totales['manzanas'])
        por_man += porcentaje_mz
        
        tabla[key] = {'numero': numero, 'porcentaje_num': porcentaje_num,
                      'manzanas': manzanas, 'porcentaje_mz': porcentaje_mz}
               
    totales['porcentaje_numero'] = por_num
    totales['porcentaje_manzana'] = round(por_man)                  
    #calculando los promedios
    lista = []
    cero = 0
    rango1 = 0
    rango2 = 0
    rango3 = 0
    rango4 = 0
    for x in consulta:
        query = UsoTierra.objects.filter(encuesta=x, tierra=1).aggregate(AreaSuma=Sum('area'))
        lista.append([x.id,query])

    for nose in lista:
        if nose[1]['AreaSuma'] == 0:
            cero += 1
        if nose[1]['AreaSuma'] >= 0.1 and  nose[1]['AreaSuma'] <= 10:
            rango1 += 1
        if nose[1]['AreaSuma'] >= 11 and nose[1]['AreaSuma'] <= 25:
            rango2 += 1
        if nose[1]['AreaSuma'] >= 26 and nose[1]['AreaSuma'] <= 50:
            rango3 += 1
        if nose[1]['AreaSuma'] >=51:
            rango4 += 1
    total_rangos = cero + rango1 + rango2 + rango3 + rango4
    por_cero = round(saca_porcentajes(cero,total_rangos),2)
    por_rango1 = round(saca_porcentajes(rango1,total_rangos),2)
    por_rango2 = round(saca_porcentajes(rango2,total_rangos),2)
    por_rango3 = round(saca_porcentajes(rango3,total_rangos),2)
    por_rango4 = round(saca_porcentajes(rango4,total_rangos),2)
    total_porcentajes = round((por_cero + por_rango1 + por_rango2 + por_rango3 + por_rango4),1)
        
    return render_to_response('reforestacion/fincas.html', locals(),
                              context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#Tabla Existencia Arboles
@session_required
def arboles(request):
    '''Tabla de arboles'''
    #******Variables***************
    a = _queryset_filtrado(request)
    num_familias = a.count()
    #******************************
    
    #**********Reforestacion************************
    tabla = {}
    totales = {}
    totales['numero'] = a.aggregate(numero = Count('reforestacion__reforestacion'))['numero']
    totales['porcentaje_nativos'] = 100
    totales['nativos'] = a.aggregate(nativo=Sum('reforestacion__respuesta'))['nativo']

    
    for activ in Actividad.objects.all():
        key = slugify(activ.nombre).replace('-', '_')
        query = a.filter(reforestacion__reforestacion = activ)
        numero = query.count()
        porcentaje_num = saca_porcentajes(numero, num_familias)
       
        tabla[key] = {'numero': numero, 'porcentaje_num':porcentaje_num 
                      }
        
    
    return  render_to_response('reforestacion/arboles.html',
                               locals(),
                               context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#Tabla Animales en la finca
@session_required
def animales(request):
    '''Los animales y la produccion'''
    consulta = _queryset_filtrado(request)
    tabla = []
    tabla_produccion = []
    totales = {}

    totales['numero'] = consulta.count() 
    totales['porcentaje_num'] = 100
    totales['animales'] = consulta.aggregate(cantidad=Sum('animalesfinca__cantidad'))['cantidad']
    totales['porcentaje_animal'] = 100

    for animal in Animales.objects.all():
        query = consulta.filter(animalesfinca__animales = animal)
        numero = query.distinct().count()
        try:
            producto = AnimalesFinca.objects.filter(animales = animal)[0].produccion
        except:
            #el animal no tiene producto aún
            continue

        porcentaje_num = saca_porcentajes(numero, totales['numero'], False)
        animales = query.aggregate(cantidad = Sum('animalesfinca__cantidad'),
                                   venta_libre = Sum('animalesfinca__venta_libre'),
                                   venta_organizada = Sum('animalesfinca__venta_organizada'),
                                   total_produccion = Sum('animalesfinca__total_produccion'),
                                   consumo = Sum('animalesfinca__consumo')
                                   )
        try:
            total = animales['consumo'] + animales['venta_libre'] + animales['venta_organizada']
        
        except:
            total = 0

        try:
            animal_familia = float(animales['cantidad'])/float(numero) 
        except:
            animal_familia = 0
        animal_familia = "%.2f" % animal_familia
        tabla.append([animal.nombre, numero, porcentaje_num,
                      animales['cantidad'], animal_familia])
        try:
            tabla_produccion.append([animal.nombre, animales['cantidad'], 
                                 producto.nombre, producto.unidad,
                                 animales['total_produccion'],
                                 animales['consumo'], 
                                 animales['venta_libre'], 
                                 animales['venta_organizada'],
                                 total
                                 ])
        except:
            pass

    

    return render_to_response('animales/animales.html', 
                              {'tabla':tabla, 'totales': totales, 
                               'num_familias': consulta.count(),
                               'tabla_produccion': tabla_produccion},
                              context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#Tabla Cultivos
@session_required
def cultivos(request):
    '''tabla los cultivos y produccion'''
    #******Variables***************
    a = _queryset_filtrado(request)
    num_familias = a.count()
    #******************************
    #**********calculosdelasvariables*****
    tabla = {} 
    for i in Cultivos.objects.all():
        key = slugify(i.nombre).replace('-', '_')
        key2 = slugify(i.unidad).replace('-', '_')
        query = a.filter(cultivosfinca__cultivos = i)
        #totales = query.aggregate(total=Sum('cultivosfinca__total'))['total']
        consumo = query.aggregate(consumo=Sum('cultivosfinca__consumo'))['consumo']
        libre = query.aggregate(libre=Sum('cultivosfinca__venta_libre'))['libre']
        organizada =query.aggregate(organizada=Sum('cultivosfinca__venta_organizada'))['organizada']
        tabla[key] = {'key2':key2,'consumo':consumo,'libre':libre,'organizada':organizada}
    
    return render_to_response('cultivos/cultivos.html',
                             {'tabla':tabla,'num_familias':num_familias},
                             context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#tabla opciones de manejo                               
@session_required                               
def opcionesmanejo(request):
    '''Opciones de manejo agroecologico'''
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    #******************************************
    tabla = {}
    
    for k in ManejoAgro.objects.all():
        key = slugify(k.nombre).replace('-','_')
        query = a.filter(opcionesmanejo__uso = k)
        frecuencia = query.count()
        nada = query.filter(opcionesmanejo__uso=k,
                            opcionesmanejo__nivel=1).aggregate(nada=Count('opcionesmanejo__nivel'))['nada']
        por_nada = saca_porcentajes(nada, num_familia)
        poco = query.filter(opcionesmanejo__uso=k,
                            opcionesmanejo__nivel=2).aggregate(poco=Count('opcionesmanejo__nivel'))['poco']
        por_poco = saca_porcentajes(poco, num_familia)
        algo = query.filter(opcionesmanejo__uso=k,
                            opcionesmanejo__nivel=3).aggregate(algo=Count('opcionesmanejo__nivel'))['algo']
        por_algo = saca_porcentajes(algo, num_familia)
        bastante = query.filter(opcionesmanejo__uso=k,
                                opcionesmanejo__nivel=4).aggregate(bastante=Count('opcionesmanejo__nivel'))['bastante']
        por_bastante = saca_porcentajes(bastante, num_familia)
        
        tabla[key] = {'nada':nada,'poco':poco,'algo':algo,'bastante':bastante,
                      'por_nada':por_nada,'por_poco':por_poco,'por_algo':por_algo,
                      'por_bastante':por_bastante}
    tabla_escala = {}                 
    for u in ManejoAgro.objects.all():
        key = slugify(u.nombre).replace('-','_')
        query = a.filter(opcionesmanejo__uso = u)
        frecuencia = query.count()
        menor_escala = query.filter(opcionesmanejo__uso=u,
                                    opcionesmanejo__menor_escala=1).aggregate(menor_escala=
                                    Count('opcionesmanejo__menor_escala'))['menor_escala']
        menor_escala2 = query.filter(opcionesmanejo__uso=u,
                                     opcionesmanejo__menor_escala=2).aggregate(menor_escala2=
                                     Count('opcionesmanejo__menor_escala'))['menor_escala2']
        total_menor = menor_escala + menor_escala2
        por_menor_escala = saca_porcentajes(menor_escala,num_familia)
        
        # vamos ahora con la mayor escala
        
        mayor_escala = query.filter(opcionesmanejo__uso=u,
                                    opcionesmanejo__mayor_escala=1).aggregate(mayor_escala=
                                    Count('opcionesmanejo__mayor_escala'))['mayor_escala']
        mayor_escala2 = query.filter(opcionesmanejo__uso=u,
                                    opcionesmanejo__mayor_escala=2).aggregate(mayor_escala2=
                                    Count('opcionesmanejo__mayor_escala'))['mayor_escala2']
        total_mayor = mayor_escala + mayor_escala2
        por_mayor_escala = saca_porcentajes(mayor_escala, num_familia)
        tabla_escala[key] = {'menor_escala':menor_escala,'menor_escala2':menor_escala2,
                             'mayor_escala':mayor_escala,'mayor_escala2':mayor_escala2,
                             'por_menor_escala':por_menor_escala,'por_mayor_escala':por_mayor_escala}
                             
                                          
    return render_to_response('agroecologico/manejo_agro.html',{'tabla':tabla,
                              'num_familias':num_familia,'tabla_escala':tabla_escala},
                               context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#tabla suelos                               
@session_required
def suelos(request):
    '''Uso del suelos'''
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    #******************************************
    tabla_textura = {}
    
    #caracteristicas del terrenos
    for k in Textura.objects.all():
        key = slugify(k.nombre).replace('-','_')
        query = a.filter(suelo__textura = k)
        frecuencia = query.count()
        textura = query.filter(suelo__textura=k).aggregate(textura=Count('suelo__textura'))['textura']
        por_textura = saca_porcentajes(textura, num_familia)
        tabla_textura[key] = {'textura':textura,'por_textura':por_textura}
        
    #profundidad del terrenos
    tabla_profundidad = {}
    
    for u in Profundidad.objects.all():
        key = slugify(u.nombre).replace('-','_')
        query = a.filter(suelo__profundidad = u)
        frecuencia = query.count()
        profundidad = query.filter(suelo__profundidad=u).aggregate(profundidad=Count('suelo__profundidad'))['profundidad']
        por_profundidad = saca_porcentajes(profundidad, num_familia)
        tabla_profundidad[key] = {'profundidad':profundidad,'por_profundidad':por_profundidad}
        
    #profundidad del lombrices
    tabla_lombrices = {}
    
    for j in Densidad.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(suelo__lombrices = j)
        frecuencia = query.count()
        lombrices = query.filter(suelo__lombrices=j).aggregate(lombrices=Count('suelo__lombrices'))['lombrices']
        por_lombrices = saca_porcentajes(lombrices, num_familia)
        tabla_lombrices[key] = {'lombrices':lombrices,'por_lombrices':por_lombrices}

     #Densidad
    tabla_densidad = {}
    
    for j in Densidad.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(suelo__densidad = j)
        frecuencia = query.count()
        densidad = query.filter(suelo__densidad=j).aggregate(densidad=Count('suelo__densidad'))['densidad']
        por_densidad = saca_porcentajes(densidad, num_familia)
        tabla_densidad[key] = {'densidad':densidad,'por_densidad':por_densidad}
        
      #Pendiente
    tabla_pendiente = {}
    
    for j in Pendiente.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(suelo__densidad = j)
        frecuencia = query.count()
        pendiente = query.filter(suelo__pendiente=j).aggregate(pendiente=Count('suelo__pendiente'))['pendiente']
        por_pendiente = saca_porcentajes(pendiente, num_familia)
        tabla_pendiente[key] = {'pendiente':pendiente,'por_pendiente':por_pendiente}
        
      #Drenaje
    tabla_drenaje = {}
    
    for j in Drenaje.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(suelo__drenaje = j)
        frecuencia = query.count()
        drenaje = query.filter(suelo__drenaje=j).aggregate(drenaje=Count('suelo__drenaje'))['drenaje']
        por_drenaje = saca_porcentajes(drenaje, num_familia)
        tabla_drenaje[key] = {'drenaje':drenaje,'por_drenaje':por_drenaje}
        
    #Materia
    tabla_materia = {}
    
    for j in Densidad.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(suelo__materia = j)
        frecuencia = query.count()
        materia = query.filter(suelo__materia=j).aggregate(materia=Count('suelo__materia'))['materia']
        por_materia = saca_porcentajes(materia, num_familia)
        tabla_materia[key] = {'materia':materia,'por_materia':por_materia}
        
    return render_to_response('suelo/suelos.html',{'tabla_textura':tabla_textura,
                              'tabla_profundidad':tabla_profundidad,'tabla_densidad':tabla_densidad,
                              'tabla_lombrices':tabla_lombrices,'tabla_pendiente':tabla_pendiente,
                              'tabla_drenaje':tabla_drenaje,'tabla_materia':tabla_materia,
                              'num_familias':num_familia},
                               context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#tabla manejo de suelo
@session_required        
def manejosuelo(request):
    ''' Manejo del suelos'''
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    #******************************************
    
    #Terrenos
    tabla_terreno = {}
    for j in Preparar.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(manejosuelo__preparan = j)
        frecuencia = query.count()
        preparan = query.filter(manejosuelo__preparan=j).aggregate(preparan=Count('manejosuelo__preparan'))['preparan']
        por_preparan = saca_porcentajes(preparan, num_familia)
        tabla_terreno[key] = {'preparan':preparan,'por_preparan':por_preparan}
        
    #Tracción
    tabla_traccion = {}
    for j in Traccion.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(manejosuelo__traccion = j)
        frecuencia = query.count()
        traccion = query.filter(manejosuelo__traccion=j).aggregate(traccion=Count('manejosuelo__traccion'))['traccion']
        por_traccion = saca_porcentajes(traccion, num_familia)
        tabla_traccion[key] = {'traccion':traccion,'por_traccion':por_traccion}
        
    #Fertilización
    tabla_fertilizacion = {}
    for j in Fertilizacion.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(manejosuelo__fertilizacion = j)
        frecuencia = query.count()
        fertilizacion = query.filter(manejosuelo__fertilizacion=j).aggregate(fertilizacion=Count('manejosuelo__fertilizacion'))['fertilizacion']
        por_fertilizacion = saca_porcentajes(fertilizacion, num_familia)
        tabla_fertilizacion[key] = {'fertilizacion':fertilizacion,
                                    'por_fertilizacion':por_fertilizacion}
                                    
    #Tipo obra de conservación del suelo
    tabla_obra = {}
    for j in Conservacion.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(manejosuelo__obra = j)
        frecuencia = query.count()
        obra = query.filter(manejosuelo__obra=j).aggregate(obra=Count('manejosuelo__obra'))['obra']
        por_obra = saca_porcentajes(obra, num_familia)
        tabla_obra[key] = {'obra':obra,'por_obra':por_obra}
        
    return render_to_response('suelo/manejo_suelo.html',{'tabla_terreno':tabla_terreno,
                              'tabla_traccion':tabla_traccion,'tabla_fertilizacion':tabla_fertilizacion,
                              'tabla_obra':tabla_obra,'num_familias':num_familia},
                               context_instance=RequestContext(request))  
#-------------------------------------------------------------------------------
                #Tabla Ingreso familiar y otros ingresos
#-------------------------------------------------------------------------------
def total_ingreso(request, numero):
    #******Variables***************
    a = _queryset_filtrado(request)
    num_familias = a.count()
    #******************************
    #*******calculos de las variables ingreso************
    tabla = {}
    for i in Rubros.objects.filter(categoria=numero):
        key = slugify(i.nombre).replace('-','_')
        key2 = slugify(i.unidad).replace('-','_')
        query = a.filter(ingresofamiliar__rubro = i)
        numero = query.count()
        cantidad = query.aggregate(cantidad=Sum('ingresofamiliar__cantidad'))['cantidad']
        precio = query.aggregate(precio=Avg('ingresofamiliar__precio'))['precio']
        ingreso = cantidad * precio if cantidad != None and precio != None else 0
        if numero > 0:
            tabla[key] = {'key2':key2,'numero':numero,'cantidad':cantidad,
                          'precio':precio,'ingreso':ingreso}
                      
    return tabla

@session_required
def ingresos(request):
    '''tabla de ingresos'''
    #******Variables***************
    a = _queryset_filtrado(request)
    num_familias = a.count()
    #******************************
    #*******calculos de las variables ingreso************
    respuesta = {}
    respuesta['bruto']= 0
    respuesta['ingreso']=0
    respuesta['ingreso_total']=0
    respuesta['ingreso_otro']=0
    respuesta['brutoo'] = 0
    respuesta['total_neto'] = 0
    agro = total_ingreso(request,1)
    forestal = total_ingreso(request,2)
    grano_basico = total_ingreso(request,3)
    ganado_mayor = total_ingreso(request,4)
    patio = total_ingreso(request,5)
    frutas = total_ingreso(request,6)
    musaceas = total_ingreso(request,7)
    raices = total_ingreso(request,8)
    
    total_agro = 0
    c_agro = 0
    for k,v in agro.items():
        total_agro += round(v['ingreso'],1)
        if v['numero'] > 0:
            c_agro += 1
    total_forestal = 0
    c_forestal = 0
    for k,v in forestal.items():
        total_forestal += round(v['ingreso'],1)
        if v['numero'] > 0:
            c_forestal += 1
    total_basico = 0
    c_basico = 0
    for k,v in grano_basico.items():
        total_basico += round(v['ingreso'],1)
        if v['numero'] > 0:
            c_basico += 1
    total_ganado = 0
    c_ganado = 0
    for k,v in ganado_mayor.items():
        total_ganado += round(v['ingreso'],1)
        if v['numero'] > 0:
            c_ganado += 1
    total_patio = 0
    c_patio = 0
    for k,v in patio.items():
        total_patio += round(v['ingreso'],1)
        if v['numero'] > 0:
            c_patio += 1
    total_fruta = 0
    c_fruta = 0
    for k,v in frutas.items():
        total_fruta += round(v['ingreso'],1)
        if v['numero'] > 0:
            c_fruta += 1
    total_musaceas = 0
    c_musaceas = 0
    for k,v in musaceas.items():
        total_musaceas += round(v['ingreso'],1)
        if v['numero'] > 0:
            c_musaceas += 1
    total_raices = 0
    c_raices = 0
    for k,v in raices.items():
        total_raices += round(v['ingreso'],1)
        if v['numero'] > 0:
            c_raices += 1
            
    respuesta['ingreso'] = total_agro + total_forestal + total_basico + total_ganado + total_patio + total_fruta + total_musaceas + total_raices
    grafo = []
    grafo.append({'Agroforestales':total_agro,'Forestales':total_forestal,'Granos_basicos':total_basico,
                  'Ganado_mayor':total_ganado,'Animales_de_patio':total_patio,
                  'Hortalizas_y_frutas':total_fruta,'Musaceas':total_musaceas,
                  'Tuberculos_y_raices':total_raices})
    cuantos = []
    cuantos.append({'Agroforestales':c_agro,'Forestales':c_forestal,'Granos_basicos':c_basico,
                  'Ganado_mayor':c_ganado,'Animales_de_patio':c_patio,
                  'Hortalizas_y_frutas':c_fruta,'Musaceas':c_musaceas,
                  'Tuberculos_y_raices':c_raices})
        
    #********* calculos de las variables de otros ingresos******
    matriz = {}
    for j in Fuentes.objects.all():
        key = slugify(j.nombre).replace('-','_')
        consulta = a.filter(otrosingresos__fuente = j)
        frecuencia = consulta.count()
        meses = consulta.aggregate(meses=Sum('otrosingresos__meses'))['meses']
        ingreso = consulta.aggregate(ingreso=Avg('otrosingresos__ingreso'))['ingreso']
        try:
            ingresototal = round(meses * ingreso,2)
        except:
            ingresototal = 0
        respuesta['ingreso_otro'] +=  ingresototal
        #ingresototal = consulta.aggregate(meses=Avg('otrosingresos__meses'))['meses'] * consulta.aggregate(ingreso=Avg('otrosingresos__ingreso'))['ingreso'] if meses != None and ingreso != None else 0
        #ingresototal = consulta.aggregate(total=Avg('otrosingresos__ingreso_total'))['total']
        matriz[key] = {'frecuencia':frecuencia,'meses':meses,
                       'ingreso':ingreso,'ingresototal':ingresototal}
                       
    try:                   
        respuesta['bruto'] = round((respuesta['ingreso'] + respuesta['ingreso_otro']) / num_familias,2)
    except:
        pass
    respuesta['total_neto'] = round(respuesta['bruto'] * 0.6,2)
        
    return render_to_response('ingresos/ingreso.html',locals(),
                              context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
                         #bienes
#-------------------------------------------------------------------------------
# Tabla equipo, infrestructura, herramientas y medio de transporte
@session_required
def equipos(request):
    '''tabla de equipos'''
    #******** variables globales***********
    a = _queryset_filtrado(request)
    num_familia = a.count()
    #*************************************
    
    #********** tabla de equipos *************
    tabla = {}
    totales = {}
    
    totales['numero'] = a.aggregate(numero=Count('propiedades__equipo'))['numero']
    totales['porciento_equipo'] = 100
    totales['cantidad_equipo'] = a.aggregate(cantidad=Sum('propiedades__cantidad_equipo'))['cantidad']
    totales['porciento_cantidad'] = 100
    
    for i in Equipos.objects.all():
        key = slugify(i.nombre).replace('-','_')
        query = a.filter(propiedades__equipo = i)
        frecuencia = query.count()
        por_equipo = saca_porcentajes(frecuencia, num_familia)
        equipo = query.aggregate(equipo=Sum('propiedades__cantidad_equipo'))['equipo']
        cantidad_pro = query.aggregate(cantidad_pro=Avg('propiedades__cantidad_equipo'))['cantidad_pro']
        tabla[key] = {'frecuencia':frecuencia, 'por_equipo':por_equipo,
                      'equipo':equipo,'cantidad_pro':cantidad_pro}
    
    #******** tabla de infraestructura *************
    tabla_infra = {}
    totales_infra = {}
    
    totales_infra['numero'] = a.aggregate(numero=Count('infraestructura__infraestructura'))['numero']
    totales_infra['porciento_infra'] = 100
    totales_infra['cantidad_infra'] = a.aggregate(cantidad_infra=Sum('infraestructura__cantidad_infra'))['cantidad_infra']
    totales_infra['por_cantidad_infra'] = 100
       
    for j in Infraestructuras.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(infraestructura__infraestructura = j)
        frecuencia = query.count()
        por_frecuencia = saca_porcentajes(frecuencia, num_familia)
        infraestructura = query.aggregate(infraestructura=Sum('infraestructura__cantidad_infra'))['infraestructura']
        infraestructura_pro = query.aggregate(infraestructura_pro=Avg('infraestructura__cantidad_infra'))['infraestructura_pro']
        tabla_infra[key] = {'frecuencia':frecuencia, 'por_frecuencia':por_frecuencia,
                             'infraestructura':infraestructura,
                             'infraestructura_pro':infraestructura_pro}
                             
    #******************* tabla de herramientas ***************************
    herramienta = {}
    totales_herramientas = {}
    
    totales_herramientas['numero'] = a.aggregate(numero=Count('herramientas__herramienta'))['numero']
    totales_herramientas['porciento_herra'] = 100
    totales_herramientas['cantidad_herra'] = a.aggregate(cantidad=Sum('herramientas__numero'))['cantidad']
    totales_herramientas['porciento_herra'] = 100
    
    for k in NombreHerramienta.objects.all():
        key = slugify(k.nombre).replace('-','_')
        query = a.filter(herramientas__herramienta = k)
        frecuencia = query.count()
        por_frecuencia = saca_porcentajes(frecuencia, num_familia)
        herra = query.aggregate(herramientas=Sum('herramientas__numero'))['herramientas']
        por_herra = query.aggregate(por_herra=Avg('herramientas__numero'))['por_herra']
        herramienta[key] = {'frecuencia':frecuencia, 'por_frecuencia':por_frecuencia,
                            'herra':herra,'por_herra':por_herra}
                            
    #*************** tabla de transporte ***********************
    transporte = {}
    totales_transporte = {}
    
    totales_transporte['numero'] = a.aggregate(numero=Count('transporte__transporte'))['numero']
    totales_transporte['porciento_trans'] = 100
    totales_transporte['cantidad_trans'] = a.aggregate(cantidad=Sum('transporte__numero'))['cantidad']
    totales_transporte['porciento_trans'] = 100
    
    for m in NombreTransporte.objects.all():
        key = slugify(m.nombre).replace('-','_')
        query = a.filter(transporte__transporte = m)
        frecuencia = query.count()
        por_frecuencia = saca_porcentajes(frecuencia, num_familia)
        trans = query.aggregate(transporte=Sum('transporte__numero'))['transporte']
        por_trans = query.aggregate(por_trans=Avg('transporte__numero'))['por_trans']
        transporte[key] = {'frecuencia':frecuencia,'por_frecuencia':por_frecuencia,
                           'trans':trans,'por_trans':por_trans}
           
    return render_to_response('bienes/equipos.html', {'tabla':tabla,'totales':totales,
                              'num_familias':num_familia,'tabla_infra':tabla_infra,
                              'herramienta':herramienta,'transporte':transporte},
                               context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#Tabla seguridad alimentaria
def alimentos(request,numero):
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    #******************************************
    tabla = {}
    
    for u in Alimentos.objects.filter(categoria=numero):
        key = slugify(u.nombre).replace('-','_')
        query = a.filter(seguridad__alimento = u)
        frecuencia = query.count()
        producen = query.filter(seguridad__alimento=u,seguridad__producen=1).aggregate(producen=Count('seguridad__producen'))['producen']
        por_producen = saca_porcentajes(producen, num_familia)
        compran = query.filter(seguridad__alimento=u,seguridad__compran=1).aggregate(compran=Count('seguridad__compran'))['compran']
        por_compran = saca_porcentajes(compran, num_familia)
        consumen = query.filter(seguridad__alimento=u,seguridad__consumen=1).aggregate(consumen=Count('seguridad__consumen'))['consumen']
        por_consumen = saca_porcentajes(consumen, num_familia)
        invierno = query.filter(seguridad__alimento=u,seguridad__consumen_invierno=1).aggregate(invierno=Count('seguridad__consumen_invierno'))['invierno']
        por_invierno = saca_porcentajes(invierno, num_familia)
        tabla[key] = {'frecuencia':frecuencia, 'producen':producen, 'por_producen':por_producen,
                      'compran':compran,'por_compran':por_compran,'consumen':consumen, 
                      'por_consumen':int(por_consumen), 'invierno':invierno,
                      'por_invierno':int(por_invierno)}
    return tabla


@session_required
def seguridad_alimentaria(request):
    '''Seguridad Alimentaria'''
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    num_familias = num_familia
    #******************************************
    
    carbohidrato = alimentos(request,1)
    grasa = alimentos(request,2)
    minerales = alimentos(request,3)
    proteinas = alimentos(request,4)
    lista = []
    carbo = 0
    for k,v in carbohidrato.items():
        if v['producen'] > 0:
            carbo += 1
            
    gra = 0
    for k,v in grasa.items():
        if v['producen'] > 0:
            gra += 1
            
    mine = 0
    for k,v in minerales.items():
        if v['producen'] > 0:
            mine += 1
            
    prot = 0
    for k,v in proteinas.items():
        if v['producen'] > 0:
            prot += 1      
    lista.append({'Carbohidrato':carbo,'Grasa':gra,'Minerales/Vitamina':mine,'Proteinas':prot}) 
                                 
    return render_to_response('seguridad/seguridad.html',locals(),
                               context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#tabla finca vulnerable
def graves(request,numero):
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    #******************************************
    suma = 0
    for p in Graves.objects.all():
        fenomeno = a.filter(vulnerable__motivo__id=numero, vulnerable__respuesta=p).count()
        suma += fenomeno
        
    lista = []
    for x in Graves.objects.all():
        fenomeno = a.filter(vulnerable__motivo__id=numero, vulnerable__respuesta=x).count()
        porcentaje = round(saca_porcentajes(fenomeno,suma),2)
        lista.append([x.nombre,fenomeno,porcentaje])        
    return lista
    
def suma_graves(request,numero):
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    #******************************************
    suma = 0
    for p in Graves.objects.all():
        fenomeno = a.filter(vulnerable__motivo__id=numero, vulnerable__respuesta=p).count()
        suma += fenomeno
    return suma

@session_required
def vulnerable(request):
    ''' Cuales son los Riesgos que hace las fincas vulnerables '''
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    num_familias = num_familia
    #******************************************
    
    #fenomenos naturales
    sequia = graves(request,1)
    total_sequia = suma_graves(request,1)
    inundacion = graves(request,2)
    total_inundacion = suma_graves(request,2)
    vientos = graves(request,3)
    total_vientos = suma_graves(request,3)
    deslizamiento = graves(request,4)
    total_deslizamiento = suma_graves(request,4)
    
    #Razones agricolas
    falta_semilla = graves(request,5)
    total_falta_semilla = suma_graves(request,5)
    mala_semilla = graves(request,6)
    total_mala_semilla = suma_graves(request,6)
    plagas = graves(request,7)
    total_plagas = suma_graves(request,7)
    
    #Razones de mercado
    bajo_precio = graves(request,8)
    total_bajo_precio = suma_graves(request,8)
    falta_venta = graves(request,9)
    total_falta_venta = suma_graves(request,9)
    estafa = graves(request,10)
    total_estafa = suma_graves(request,10)
    falta_calidad = graves(request,11)
    total_falta_calidad = suma_graves(request,11)
    
    #inversion
    falta_credito = graves(request,12)
    total_falta_credito = suma_graves(request,12)
    alto_interes = graves(request,13)
    total_alto_interes = suma_graves(request,13)     
            
#    lista2 = []
#    for i in Fenomeno.objects.all():
#        key = slugify(i.nombre).replace('-','_')
#        key2 = slugify(i.causa.nombre).replace('-','_')
#        query = a.filter(vulnerable__motivo = i)
#        frecuencia = query.count()
#        porce = saca_porcentajes(frecuencia,num_familia)    
#        lista2.append([key,key2,frecuencia,porce])
    
    return render_to_response('riesgos/vulnerable.html', locals(),
                              context_instance=RequestContext(request))
#-------------------------------------------------------------------------------
#tabla mitigacion de riesgos
@session_required    
def mitigariesgos(request):
    ''' Mitigación de los Riesgos '''
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    #******************************************
    tabla = {}
    for j in PreguntaRiesgo.objects.all():
        key = slugify(j.nombre).replace('-','_')
        query = a.filter(riesgos__pregunta = j)
        mitigacion = query.filter(riesgos__pregunta=j, riesgos__respuesta=1).aggregate(mitigacion=Count('riesgos__pregunta'))['mitigacion']
        por_mitigacion = saca_porcentajes(mitigacion, num_familia)
        tabla[key] = {'mitigacion':mitigacion,'por_mitigacion':por_mitigacion}
        
    return render_to_response('riesgos/mitigacion.html',{'tabla':tabla,
                              'num_familias':num_familia},
                               context_instance=RequestContext(request)) 
#-------------------------------------------------------------------------------
@session_required
def plantaciones(request):
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    promedio_planta = 0
    promedio_injerto = 0
    #Lista de los viveros
    vivero = []
#    for viver in Vivero.objects.all():
        #cuantos tiene
    conteo = a.filter(vivero__vivero_cacao = 1).count()
    frecuencia = round(saca_porcentajes(conteo,num_familia))
        #numero de plantas
    total_planta = a.aggregate(total_planta=Sum('vivero__plantas'))['total_planta']
    try:
        promedio_planta = round(total_planta / conteo)
    except:
        pass
        #numero de plantas injertadas
    n_injertada = a.aggregate(n_injertada=Sum('vivero__planta_injerto'))['n_injertada']
    try:
        promedio_injerto = round(n_injertada / conteo)
    except:
        pass
    vivero = (conteo,frecuencia,'---','---',total_planta,promedio_planta,n_injertada,
              promedio_injerto)
        
    planta_menos = []
#    for menos in PlantaDesarrolloMenos.objects.all():
        #cuantos tiene
    conteo_m = a.filter(plantadesarrollomenos__cacao_desarrollo = 1).count()
    frecuencia_m = round(saca_porcentajes(conteo_m,num_familia))
        #areas
    area_total_m = a.aggregate(area_total_m=Sum('plantadesarrollomenos__area_sembrada'))['area_total_m']
    try:
        promedio_area_m = round(area_total_m / conteo_m)
    except:
        promedio_area_m = 0
        #numero de plantas
    total_planta_m = a.aggregate(total_planta_m=Sum('plantadesarrollomenos__plantas_finca'))['total_planta_m']
    try:
        promedio_planta_m = round(total_planta_m / conteo_m)
    except:
        promedio_planta_m = 0
        #numero de plantas injertadas
    n_injertada_m = a.aggregate(n_injertada_m=Sum('plantadesarrollomenos__planta_injerto'))['n_injertada_m']
    try:
        promedio_injerto_m = round(n_injertada_m / conteo_m)
    except:
        promedio_injerto_m = 0
        
    planta_menos = (conteo_m,frecuencia_m,area_total_m,promedio_area_m,total_planta_m,
                    promedio_planta_m,n_injertada_m,promedio_injerto_m)
                        
    planta_mas = []
    for menos in PlantaDesarrolloMas.objects.all():
        #cuantos tiene
        conteo = a.filter(plantadesarrollomas__cacao_desarrollo = 1).count()
        frecuencia = round(saca_porcentajes(conteo,num_familia))
        #areas
        area_total = a.aggregate(area_total=Sum('plantadesarrollomas__area_sembrada'))['area_total']
        promedio_area = round(area_total / conteo)
        #numero de plantas
        total_planta = a.aggregate(total_planta=Sum('plantadesarrollomas__plantas_finca'))['total_planta']
        promedio_planta = round(total_planta / conteo)
        #numero de plantas injertadas
        n_injertada = a.aggregate(n_injertada=Sum('plantadesarrollomas__planta_injerto'))['n_injertada']
        promedio_injerto = round(n_injertada / conteo)
        planta_mas = (conteo,frecuencia,area_total,promedio_area,total_planta,
                        promedio_planta,n_injertada,promedio_injerto)
                        
    planta_produccion = []
    for menos in PlantaProduccion.objects.all():
        #cuantos tiene
        conteo = a.filter(plantaproduccion__plantas_cacao = 1).count()
        frecuencia = round(saca_porcentajes(conteo,num_familia))
        #areas
        area_total = a.aggregate(area_total=Sum('plantaproduccion__area_sembrada'))['area_total']
        promedio_area = round(area_total / conteo)
        #numero de plantas
        total_planta = a.aggregate(total_planta=Sum('plantaproduccion__plantas_finca'))['total_planta']
        promedio_planta = round(total_planta / conteo)
        #numero de plantas injertadas
        n_injertada = a.aggregate(n_injertada=Sum('plantaproduccion__planta_injerto'))['n_injertada']
        promedio_injerto = round(n_injertada / conteo)
        planta_produccion = (conteo,frecuencia,area_total,promedio_area,total_planta,
                        promedio_planta,n_injertada,promedio_injerto)
                        
    planta_elite = []
    for elite in PlantaElite.objects.all():
        #cuantos tiene
        conteo = a.filter(plantaelite__elite = 1).count()
        frecuencia = round(saca_porcentajes(conteo,num_familia))
        #numero de plantas
        total_planta = a.aggregate(total_planta=Sum('plantaelite__cuantas'))['total_planta']
        try:
            promedio_planta = round(total_planta / conteo)
        except:
            promedio_planta = 0
        planta_elite = (conteo,frecuencia,'---','---',total_planta,promedio_planta,
                        '---','---')
    
    #esto es la parte de elite produccion
    lista_total = []
    lista_sin_fermentar = []
    lista_fermentado = []
    lista_organico = []
    for prod in PlantaProduccion.objects.all():
        #total
        conteo = a.aggregate(conteo=Count('plantaproduccion__total'))['conteo']
        frecuencia= round(saca_porcentajes(conteo,num_familia))
        produccion_total = a.aggregate(produccion_total=Sum('plantaproduccion__total'))['produccion_total']
        promedio = round(produccion_total / conteo)
        porcentaje = round(saca_porcentajes(produccion_total,produccion_total))
        lista_total = (conteo,frecuencia,produccion_total,promedio,porcentaje)
        #sin fermentacion
        s_conteo = a.aggregate(s_conteo=Count('plantaproduccion__sin_fermentar'))['s_conteo']
        s_frecuencia= round(saca_porcentajes(s_conteo,num_familia))
        s_produccion_total = a.aggregate(produccion_total=Sum('plantaproduccion__sin_fermentar'))['produccion_total']
        s_promedio = round(s_produccion_total / s_conteo)
        s_porcentaje = round(saca_porcentajes(s_produccion_total,produccion_total))
        lista_sin_fermentar = (s_conteo,s_frecuencia,s_produccion_total,s_promedio,
                               s_porcentaje)               
        #fermentado
        f_conteo = a.aggregate(f_conteo=Count('plantaproduccion__fermentado'))['f_conteo']
        f_frecuencia= round(saca_porcentajes(f_conteo,num_familia))
        f_produccion_total = a.aggregate(produccion_total=Sum('plantaproduccion__fermentado'))['produccion_total']
        f_promedio = round(f_produccion_total / f_conteo)
        f_porcentaje = round(saca_porcentajes(f_produccion_total,produccion_total))
        lista_fermentado = (f_conteo,f_frecuencia,f_produccion_total,
                            s_promedio,f_porcentaje)
        #organico
        o_conteo = a.aggregate(o_conteo=Count('plantaproduccion__organico'))['o_conteo']
        o_frecuencia= round(saca_porcentajes(o_conteo,num_familia))
        o_produccion_total = a.aggregate(produccion_total=Sum('plantaproduccion__organico'))['produccion_total']
        o_promedio = round(o_produccion_total / o_conteo)
        o_porcentaje = round(saca_porcentajes(o_produccion_total,produccion_total))
        lista_organico = (o_conteo,o_frecuencia,o_produccion_total,
                          o_promedio,o_porcentaje)
    
    productividad = round(lista_total[2] / planta_produccion[2],2)
    
    #costos de la produccion
    costo_area = []
    costo_finca = []
    conteo_finca = 0
    for coso in Costo.objects.all():
        if coso.mantenimiento_area > 0:
            conteo_area = a.aggregate(conteo_area=Count('costo__mantenimiento_area'))['conteo_area']
        total_area = a.aggregate(total_area=Sum('costo__mantenimiento_area'))['total_area']
        promedio_area = round(total_area / conteo_area)
        costo_area = (conteo_area,total_area,promedio_area)
        if coso.mantenimiento_finca > 0:
            conteo_finca = a.aggregate(conteo_finca=Count('costo__mantenimiento_finca'))['conteo_finca']
        total_finca = a.aggregate(total_finca=Sum('costo__mantenimiento_finca'))['total_finca']
        try:
            promedio_finca = round(total_finca / conteo_finca)
        except:
            promedio_finca = 0
        costo_finca = (conteo_finca,total_finca,promedio_finca)

    porcentaje_cacao = round(saca_porcentajes(costo_area[1],costo_finca[1]),2)
    #costo de mantenimiento cacao/mz
    mantenimiento_cacao = round(costo_area[1] / (planta_menos[2] + planta_mas[2] + planta_produccion[2]),4)
    #costo de mantenimiento qq
    mantenimiento_qq = round(costo_area[1] / lista_total[2],2)
                
                                
    return render_to_response('estado/plantaciones.html',{'vivero':vivero,
                              'num_familias':num_familia,'planta_menos':planta_menos,
                              'planta_mas':planta_mas,'planta_produccion':planta_produccion,
                              'planta_elite':planta_elite,'lista_total':lista_total,
                              'lista_sin_fermentar':lista_sin_fermentar,
                              'lista_fermentado':lista_fermentado,'lista_organico':lista_organico,
                              'productividad':productividad,'costo_area':costo_area,
                              'costo_finca':costo_finca,'porcentaje_cacao':porcentaje_cacao,
                              'mantenimiento_cacao':mantenimiento_cacao,'mantenimiento_qq':mantenimiento_qq},
                               context_instance=RequestContext(request))  
#-------------------------------------------------------------------------------
@session_required
def tecnicas(request):
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familia = a.count()
    num_familias = num_familia
    #vivero - practica
    lista_vivero = {}
    for datos in Practicas.objects.all():
        conteo = a.filter(viveropractica__practica=datos,viveropractica__respuesta=1).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        lista_vivero[datos.nombre] = (conteo,int(porcentaje))
    dicc1 = sorted(lista_vivero.items(), key=lambda x: x[1], reverse=True)
    #---------------------------------------------------------------------------
    
    lista_fertilizacion = {}
    for datos in PracticaEtapa.objects.all():
        conteo = a.filter(practicafertilizacion__practica=datos,practicafertilizacion__respuesta=1).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        lista_fertilizacion[datos.nombre] = (conteo,int(porcentaje))
    dicc2 = sorted(lista_fertilizacion.items(), key=lambda x: x[1], reverse=True)
    #---------------------------------------------------------------------------
    
    lista_fitosanitaria = {}
    for datos in PracticaFitosanitaria.objects.all():
        conteo = a.filter(practicamanejofitosanitario__practica=datos,practicamanejofitosanitario__respuesta=1).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        lista_fitosanitaria[datos.nombre] = (conteo,int(porcentaje))
    dicc3 = sorted(lista_fitosanitaria.items(), key=lambda x: x[1], reverse=True)
    #---------------------------------------------------------------------------
    
    lista_productivo = {}
    for datos in PracticaProductivo.objects.all():
        conteo = a.filter(practicamanejoproductivo__practica=datos,practicamanejoproductivo__respuesta=1).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        lista_productivo[datos.nombre] = (conteo,int(porcentaje))
    dicc4 = sorted(lista_productivo.items(), key=lambda x: x[1], reverse=True)
    #---------------------------------------------------------------------------
    
    lista_generico = {}
    for datos in PracticaGenetico.objects.all():
        conteo = a.filter(practicamejoramientogenetico__practica=datos,practicamejoramientogenetico__respuesta=1).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        lista_generico[datos.nombre] = (conteo,int(porcentaje))
    dicc5 = sorted(lista_generico.items(), key=lambda x: x[1], reverse=True)
    #--------------------------------------------------------------------------
    
    lista_postcosecha = {}
    for datos in PracticaPostcosecha.objects.all():
        conteo = a.filter(practicamanejopostcosecha__practica=datos,practicamanejopostcosecha__respuesta=1).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        lista_postcosecha[datos.nombre] = (conteo,int(porcentaje))
    dicc6 = sorted(lista_postcosecha.items(), key=lambda x: x[1], reverse=True)

    return render_to_response('estado/practicas.html', RequestContext(request, locals()))
#-------------------------------------------------------------------------------

@session_required
def nivels(request):
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familias = num_familia = a.count()
    
    nivel_fermentacion = []
    for k in CHOICE_FERMENTACION:
        conteo = a.filter(niveles__nivel_fermentacion=k[0]).count()
#        conteo = a.filter(niveles__nivel_fermentacion=a[0]).aggregate(conteo=Count('niveles__nivel_fermentacion'))['conteo']
        porcentaje = saca_porcentajes(conteo,num_familia)
        nivel_fermentacion.append([k[1],conteo,int(porcentaje)])
    #---------------------------------------------------------------------------
    
    nivel_secado = []
    for b in CHOICE_SECADO:
        conteo = a.filter(niveles__nivel_secado=b[0]).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        nivel_secado.append([b[1], conteo, int(porcentaje)])
    #---------------------------------------------------------------------------
    
    nivel_acopio = []
    for c in CHOICE_OPCION:
        conteo = a.filter(niveles__centro_acopio=c[0]).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        nivel_acopio.append([c[1], conteo, int(porcentaje)])
    #---------------------------------------------------------------------------
    
    nivel_socio = []
    for c in CHOICE_OPCION:
        conteo = a.filter(niveles__socio=c[0]).count()
        porcentaje = saca_porcentajes(conteo,num_familia)
        nivel_socio.append([c[1],conteo,int(porcentaje)])
        
    
    return render_to_response('estado/niveles.html', RequestContext(request, locals()))         

@session_required
def comercializacion(request):
    #********variables globales****************
    productos = Productos.objects.all()
    a = _queryset_filtrado(request)
    num_familias = num_familia = a.count()     
    
    lista_producto = {}
    for comer in productos:
        conteo = a.filter(comercializacion__producto=comer).count()
        porcentaje = round(saca_porcentajes(conteo,num_familia),2)
        suma_autoconsumo = a.filter(comercializacion__producto=comer).aggregate(suma_autoconsumo=Sum('comercializacion__autoconsumo'))['suma_autoconsumo']
        suma_venta = a.filter(comercializacion__producto=comer).aggregate(suma_venta=Sum('comercializacion__venta'))['suma_venta']
        precio = a.filter(comercializacion__producto=comer).aggregate(precio=Avg('comercializacion__precio'))['precio']
        try:
            ingreso = round(suma_autoconsumo + suma_venta) * precio
        except:
            ingreso = 0
        lista_producto[comer.nombre] = (comer.unidad,conteo,
                                                 porcentaje,suma_autoconsumo,
                                                 suma_venta,precio,ingreso)
    #graficos de ventas a quien vende
    lista_vende = {}
    for producto in productos:
        lista_vende[producto.nombre] = {}
        for quien in AquienVende.objects.all():
            lista_vende[producto.nombre][quien.nombre] = a.filter(comercializacion__producto=producto,
                                                                   comercializacion__aquien_vende=quien).count()
    #print lista_vende
    
    #graficos de donde lo vende    
    lista_donde = {}
    for producto in productos:
        lista_donde[producto.nombre] = {}
        for donde in DondeVende.objects.all():
            lista_donde[producto.nombre][donde.nombre] = a.filter(comercializacion__producto=producto,
                                                                   comercializacion__donde=donde).count()
    #print lista_donde 
    
                        
    #capacitaciones
    dicc2 = {}
    for tecnica in Tecnica.objects.all():
        dicc2[tecnica.nombre] = {}
        for familia in Familia.objects.all():
            dicc2[tecnica.nombre][familia.nombre] = conteo = a.filter(capacitaciontecnica__capacitacion=tecnica,capacitaciontecnica__respuesta=familia).count()            
            
    dicc1 = {}
    for tecnica in Social.objects.all():
        dicc1[tecnica.nombre] = {}
        for familia in Familia.objects.all():
            dicc1[tecnica.nombre][familia.nombre] = conteo = a.filter(capacitacionsocial__capacitacion=tecnica,capacitacionsocial__respuesta=familia).count()
            
                                                         
    return render_to_response('comercializacion/comercio.html', RequestContext(request, locals()))    
#-------------------------------------------------------------------------------
@session_required
def generos(request):
    #********variables globales****************
    a = _queryset_filtrado(request)
    num_familias = a.filter(sexo=2).count()
    mujer = Encuesta.objects.filter(sexo=2).count()
    
    #actividad del hogar y finca
    lista_hogar = {}
    for i in ActividadHogar.objects.all():
        conteo = a.filter(participacion__principal=i, sexo=2).count()
        porcentaje = round(saca_porcentajes(conteo,mujer),2)
        lista_hogar[i.nombre]= (conteo,porcentaje)
        
    lista_finca = {}
    for b in ActividadFinca.objects.all():
        conteo = a.filter(sexo=2, participacion__actividad_finca=b).count()
        porcentaje = round(saca_porcentajes(conteo,mujer),2)
        lista_finca[b.nombre]= (conteo,porcentaje)
        
    #numero de mujeres tiene ingreso
    conteo_mujer = a.filter(sexo=2, participacion__ingreso__gt=1).aggregate(conteo_mujer=Count('participacion__ingreso'))['conteo_mujer']
    tiene_ingreso = round(saca_porcentajes(conteo_mujer,mujer))
    ingreso_mujer = a.filter(sexo=2).aggregate(ingreso_mujer=Sum('participacion__ingreso'))['ingreso_mujer']
    try:
        promedio_mujer = round(ingreso_mujer / conteo_mujer)
    except:
        pass
    
    #grafico maneja y administra los recursos
    decicion_grafico = []
    for decicion in choice_si_no:
        conteo = a.filter(participacion__decision=decicion[0], sexo=2).count()
        porcentaje = round(saca_porcentajes(conteo,num_familias),2)
        decicion_grafico.append([decicion[1],conteo,porcentaje])
    
    lista_proporcion = {}
    lista_proporcion['De 0 - 20 %'] = a.filter(participacion__proporcion__range=(0,20), sexo=2,
                      participacion__ingreso__gt=1).count()
    lista_proporcion['De 21 - 40 %'] = a.filter(participacion__proporcion__range=(21,40), sexo=2,
                      participacion__ingreso__gt=1).count()
    lista_proporcion['De 41 - 60 %'] = a.filter(participacion__proporcion__range=(41,60), sexo=2,
                      participacion__ingreso__gt=1).count()
    lista_proporcion['De 61 - 80 %'] = a.filter(participacion__proporcion__range=(61,80), sexo=2,
                      participacion__ingreso__gt=1).count()
    lista_proporcion['De 81 - 100 %'] = a.filter(participacion__proporcion__range=(81,100), sexo=2,
                      participacion__ingreso__gt=1).count()
                      
    #salidas de mujer en la Organización
    grafo_participa = []
    for c in CHOICE_OPCION:
        conteo = a.filter(mujerorganizacion__participa=c[0], sexo=2).count()
        porcentaje = round(saca_porcentajes(conteo,num_familias),2)
        grafo_participa.append([c[1],conteo,porcentaje])
        
    grafo_organizacion = []
    for c in TipoOrganizacion.objects.all():
        conteo = a.filter(mujerorganizacion__tipo_organizacion=c,
                          mujerorganizacion__participa=1, sexo=2).count()
        porcentaje = round(saca_porcentajes(conteo,num_familias),2)
        grafo_organizacion.append([c.nombre,conteo,porcentaje])
        
    grafo_voto = []
    for c in CHOICE_OPCION:
        conteo = a.filter(mujerorganizacion__voto=c[0], sexo=2).count()
        porcentaje = round(saca_porcentajes(conteo,num_familias),2)
        grafo_voto.append([c[1],conteo,porcentaje])
        
    grafo_informada = []
    for c in CHOICE_OPCION:
        conteo = a.filter(mujerorganizacion__informada=c[0], sexo=2).count()
        porcentaje = round(saca_porcentajes(conteo,num_familias),2)
        grafo_informada.append([c[1],conteo,porcentaje])
        
    grafo_ideas = []
    for c in CHOICE_OPCION:
        conteo = a.filter(mujerorganizacion__ideas_familia=c[0], sexo=2).count()
        porcentaje = round(saca_porcentajes(conteo,num_familias),2)
        grafo_ideas.append([c[1],conteo,porcentaje])
        
    grafo_comunidad = []
    for c in CHOICE_OPCION:
        conteo = a.filter(mujerorganizacion__ideas_comunidad=c[0], sexo=2).count()
        porcentaje = round(saca_porcentajes(conteo,num_familias),2)
        grafo_comunidad.append([c[1],conteo,porcentaje])
             
    return render_to_response('genero/genero.html', RequestContext(request, locals()))         
    
    
#-------------------------------------------------------------------------------    
#Los puntos en el mapa
def obtener_lista(request):    
    lista = []    
    data = {}
    for obj in Encuesta.objects.all():        
        key = 'hombres' if obj.sexo == 1 else 'mujeres'
        name = obj.comunidad.municipio.nombre
        try:                
            data[name][key] += 1
        except:
            data[name] = dict(hombres=0, mujeres=0, 
                              lon=float(obj.comunidad.municipio.longitud),
                              lat=float(obj.comunidad.municipio.latitud))
            data[name][key] += 1
                                        
    lista.append(data)    
    return HttpResponse(simplejson.dumps(lista), mimetype='application/javascript')

#-------------------------------------------------------------------------------
# Aca empieza el menu para los subindicadores :)
                               
@session_required
def familia(request):
    '''Familias: aca van las familias con sus respectivos indicadores, educacion,
       salud, energia, agua.
    '''
    familias = _queryset_filtrado(request).count()
    return render_to_response('encuestas/familia.html',
                              {'num_familias':familias},
                              context_instance=RequestContext(request))
                              
@session_required
def organizacion(request):
    '''Organizacion: aca van las organizaciones con sus respectivos indicadores,
       como son gremial y comunitaria.
    '''
    familias = _queryset_filtrado(request).count()
    return render_to_response('organizacion/organizacion.html',
                              {'num_familias':familias},
                              context_instance=RequestContext(request))
                              
@session_required
def riesgo(request):
    '''Riesgos: aca van los riesgos con sus indicadores como son: vulnerabilidad 
       en la finca asi como la mitigación de estos.
    '''
    familias = _queryset_filtrado(request).count()
    return render_to_response('riesgos/riesgos.html',
                              {'num_familias':familias},
                              context_instance=RequestContext(request))
                              
@session_required
def suelo(request):
    '''Suelo: aca va el indicador de suelo con sus subindicadores: caracteristicas
       del terrreno y manejo del suelo
    '''
    familias = _queryset_filtrado(request).count()
    return render_to_response('suelo/suelo.html',
                              {'num_familias':familias},
                              context_instance=RequestContext(request))
                              
@session_required
def tenencias(request):
    '''Tenencia: aca van las tenencias con sus respectivos subindicadores: 
       tenencia de la propiedad, documento legal, tierra etc.
    '''
    familias = _queryset_filtrado(request).count()
    return render_to_response('encuestas/tenencia.html',
                              {'num_familias':familias},
                              context_instance=RequestContext(request))
                              
@session_required
def tierra(request):
    '''Tierra: aca va el indicador uso de tierra con su respectivos subindicadores:
       uso de la tierra, existencia de arboles y reforestacion.
    '''
    familias = _queryset_filtrado(request).count()
    return render_to_response('tierra/tierra.html',
                              {'num_familias':familias},
                              context_instance=RequestContext(request))                                   
#TODO: completar esto
VALID_VIEWS = {
        'educacion': educacion,
        'luz':luz,
        'agua': agua,
        'fincas':fincas,
        'arboles': arboles,
        'animales': animales,
        'cultivos': cultivos,
        'ingresos': ingresos,
        'equipos': equipos,
        'riesgo': riesgo,
        'tierra': tierra,
        'suelo': suelo,
        'suelos': suelos,
        'familia': familia,
        'gremial': gremial,
        'tenencias': tenencias,
        #'usosemilla': usosemilla,
        'vulnerable': vulnerable,
        'manejosuelo': manejosuelo,
        'comunitario' : comunitario,
        'organizacion': organizacion,
        'mitigariesgos': mitigariesgos,
        #'ahorro_credito': ahorro_credito,
        'opcionesmanejo': opcionesmanejo,
        'seguridad': seguridad_alimentaria,
        'general': generales,           
        #17.x plantaciones
        'vivero': plantaciones,
        'tecnica': tecnicas,
        'niveles': nivels,
        'comercializacion': comercializacion,
        'genero': generos,
         
  }
        
# Vistas para obtener los municipios, comunidades, etc..
def get_munis(request):
    '''Metodo para obtener los municipios via Ajax segun los departamentos selectos'''
    ids = request.GET.get('ids', '')
    dicc = {}
    resultado = []
    if ids:
        lista = ids.split(',')    
        for id in lista:
            try:
                departamento = Departamento.objects.get(pk=id)
                municipios = Municipio.objects.filter(departamento__id=departamento.pk).order_by('nombre')
                lista1 = []
                for municipio in municipios:
                    muni = {}
                    muni['id'] = municipio.pk
                    muni['nombre'] = municipio.nombre
                    lista1.append(muni)
                    dicc[departamento.nombre] = lista1
            except:
                pass    
    
    #filtrar segun la organizacion seleccionada
    org_ids = request.GET.get('org_ids', '')
    if org_ids:
        lista = org_ids.split(',')    
        municipios = [encuesta.municipio for encuesta in Encuesta.objects.filter(organizacion__id__in=lista)]
        #crear los keys en el dicc para evitar KeyError
        for municipio in municipios:
            dicc[municipio.departamento.nombre] = []
        
        #agrupar municipios por departamento padre                
        for municipio in municipios:
            muni = {'id': municipio.id, 'nombre': municipio.nombre}
            if not muni in dicc[municipio.departamento.nombre]:
                dicc[municipio.departamento.nombre].append(muni)            
    
    resultado.append(dicc)
        
    return HttpResponse(simplejson.dumps(resultado), mimetype='application/json')

def get_comunies(request):
    ids = request.GET.get('ids', '')
    if ids:
        lista = ids.split(',')
    results = []
    comunies = Comunidad.objects.filter(municipio__pk__in=lista).order_by('nombre').values('id', 'nombre')

    return HttpResponse(simplejson.dumps(list(comunies)), mimetype='application/json')
    
def get_organi(request):
    ids = request.GET.get('ids', '')
    if ids:
        lista = ids.split(',')
    organizaciones = OrganizacionOCB.objects.filter(encuesta__municipio__departamento__in = lista).distinct().order_by('nombre').values('id', 'nombre')
       
    
    return HttpResponse(simplejson.dumps(list(organizaciones)), mimetype='application/json')


def get_municipios(request, departamento):
    municipios = Municipio.objects.filter(departamento = departamento)
    lista = [(municipio.id, municipio.nombre) for municipio in municipios]
    return HttpResponse(simplejson.dumps(lista), mimetype='application/javascript')
    
def get_organizacion(request, departamento):
    encuestas = Encuesta.objects.filter(municipio__departamento=departamento)    
    organizaciones = OrganizacionOCB.objects.filter(encuesta__in=encuestas).distinct()
    lista = [(organizacion.id, organizacion.nombre) for organizacion in organizaciones]
    return HttpResponse(simplejson.dumps(lista), mimetype='application/javascript')

def get_comunidad(request, municipio):
    comunidades = Comunidad.objects.filter(municipio = municipio )
    lista = [(comunidad.id, comunidad.nombre) for comunidad in comunidades]
    return HttpResponse(simplejson.dumps(lista), mimetype='application/javascript')
    
# Funciones utilitarias para cualquier proposito

def saca_porcentajes(values):
    """sumamos los valores y devolvemos una lista con su porcentaje"""
    total = sum(values)
    valores_cero = [] #lista para anotar los indices en los que da cero el porcentaje
    for i in range(len(values)):
        porcentaje = (float(values[i])/total)*100
        values[i] = "%.2f" % porcentaje + '%' 
    return values

def saca_porcentajes(dato, total, formato=True):
    '''Si formato es true devuelve float caso contrario es cadena'''
    if dato != None:
        try:
            porcentaje = (dato/float(total)) * 100 if total != None or total != 0 else 0
        except:
            return 0
        if formato:
            return porcentaje
        else:
            return '%.2f' % porcentaje
    else: 
        return 0

def calcular_positivos(suma, numero, porcentaje=True):
    '''Retorna el porcentaje de positivos'''
    try:
        positivos = (numero * 2) - suma
        if porcentaje:
            return '%.2f' % saca_porcentajes(positivos, numero)
        else:
            return positivos
    except:
        return 0

def calcular_negativos(suma, numero, porcentaje = True):
    positivos = calcular_positivos(suma, numero, porcentaje)
    if porcentaje:
        return 100 - float(positivos)
    else:
        return numero - positivos  
