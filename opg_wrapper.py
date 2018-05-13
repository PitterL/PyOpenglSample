from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL import arrays
from OpenGL.arrays.arraydatatype import GLfloatArray
from OpenGL.GL.VERSION import GL_1_1

import glfw
import pygame
import glm
import math
import numpy
from ctypes import sizeof, c_float, c_void_p, c_uint, c_short
from collections import OrderedDict


from tools import CData

class ShaderData(object):
    SHA_PARAM = ('vao', 'program', 'texs')
    SHA_RENDER = SHA_TRANS = ('model', 'view', 'project', 'texture')
    SHA_CALLBACK = ('begin_render', 'end_render')
    SHA_NAMES = SHA_PARAM + SHA_RENDER + SHA_CALLBACK

    def __init__(self, **kwargs):
        self._id = None
        self._param = {}
        self._trans = {}
        self._render = {}
        self._callback = {}
        self.kwargs = kwargs

        self.store_trans(self.model_transform, self.view_transform, self.project_transform, self.texture_transform)

    def set_id(self, id):
        self._id = id

    def id(self):
        return self._id

    def _set(self, root, name, value):
        assert name in self.SHA_NAMES
        root[name] = value

    def _get(self, root, name):
        if isinstance(name, (tuple, list)):
            result = []
            for n in name:
                data = root.get(n)
                result.append(data)
            return result

        assert name in self.SHA_NAMES
        return root.get(name)

    def set_param(self, name, value):
        assert name not in self._param.keys()
        self._set(self._param, name, value)

    def get_param(self, name):
        return self._get(self._param, name)

    def store_param(self, *values):
        self._param.update(dict(zip(self.SHA_PARAM, values)))

    def set_trans(self, name, value):
        #assert name not in self._trans.keys()
        self._set(self._trans, name, value)

    def get_trans(self, name):
        return self._get(self._trans, name)

    def store_trans(self, *values):
        self._trans.update(dict(zip(self.SHA_TRANS, values)))

    def set_render(self, name, value):
        assert name not in self._render.keys()
        self._set(self._render, name, value)

    def get_render(self, name):
        return self._get(self._render, name)

    def store_render(self, *values):
        self._render.update(dict(zip(self.SHA_RENDER, values)))

    def set_callback(sell, name, value):
        assert name not in self._callback.keys()
        self._set(self._callback, name, value)

    def get_callback(self, name):
        return self._get(self._callback, name)

    def store_callback(self, *values):
        self._callback.update(dict(zip(self.SHA_CALLBACK, values)))

    def do_render(self, event):
        rstart = self.get_callback('begin_render')
        rend = self.get_callback('end_render')

        rstart(self)
        for n in self.SHA_RENDER:
            trans = self.get_trans(n)
            render = self.get_render(n)
            assert all((render, trans))

            mt = trans(event)
            render(self, mt)
        rend(self)

    def refresh(self, name, vbo):
        pass

    def model_transform(self, event, **kwargs):
        return glm.mat4(1)
        #self.store_id('model', model, shader_id)

    def view_transform(self, event, **kwargs):
        # eye指定相机位置，center指定相机指向目标位置，up指定viewUp向量

        # 默认从z轴正方向观看
        # eye = glm.vec3(0, 0, -1)
        # center = glm.vec3(0, 0, 0)
        # up = glm.vec3(0, 1, 0)
        #
        # view = glm.lookAt(eye, center, up)

        view = glm.mat4(1)

        return view

    def project_transform(self, event, **kwargs):
        #return glm.mat4(1)
        #self.store_id('project', proj, shader_id)

        # w, h = self.window_size
        # proj = glm.perspective(glm.radians(45), w / h, 1, 100)

        proj = glm.mat4(1)
        return proj

    def texture_transform(self, event, **kwargs):
        pass

class OpenglWrapper():

    def __init__(self, **kwargs):
        self.window_size = None
        self.window = None
        # self.program_id = None
        # self.vao_id = None
        # self.text_id = None

        self._shaders = []

    def create_window(self, w, h, event=None):
        if not glfw.init():
            return

        self.window_size = (w, h)

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.RESIZABLE, GL_FALSE)

        # Create a windowed mode window and its OpenGL context
        window = glfw.create_window(w, h, self.__class__.__name__, None, None)
        if not window:
            glfw.terminate()
            return

        # Make the window's context current
        glfw.make_context_current(window)
        glViewport(0, 0, w, h)

        if event:
            glfw.set_key_callback(window, event.key_callback)

            # 注册鼠标事件回调函数
            glfw.set_cursor_pos_callback(window, event.mouse_move_callback)
            # 注册鼠标滚轮事件回调函数
            glfw.set_scroll_callback(window, event.mouse_scroll_callback)
            # 鼠标捕获 停留在程序内
            glfw.set_input_mode(window, glfw.CURSOR, glfw.CURSOR_DISABLED)

        self.event = event
        self.window = window

    def create_shader(self, data, vformat, vcode, fcode, textures, cls_shader=ShaderData):
        vex_data = (data, vformat, None)
        datas = {'vertex': vex_data}
        return self.create_shader_instances(datas, vcode, fcode, textures, cls_shader)

    def create_shader_instances(self, datas, vcode, fcode, textures, cls_shader=ShaderData):
        shader = cls_shader()

        #parent = self
        #vertices = self.build_data(data)
        vao = self.build_vao(datas)
        program = self.build_shader(vcode, fcode)

        texs = []
        if textures:
            if isinstance(textures, (tuple, list)):
                for tex in textures:
                    t = self.build_texture(tex)
                    texs.append(t)
            else:
                t = self.build_texture(textures)
                texs.append(t)

        param = (vao, program, texs)
        if not all(param[:-1]):
            print(self.__class__.__name__, "create_shader failed,", "[param]", param)
            return

        shader.store_param(*param)
        #shader.store_trans(self.model_transform, self.view_transform, self.project_transform, self.texture_transform)
        shader.store_render(self.render_model, self.render_view, self.render_proj, self.render_texture)
        shader.store_callback(self._render_start, self._render_end)
        shader.set_id(len(self._shaders))

        self._shaders.append(shader)
        return shader

    def set_shader(self, type, name, value, shader_id=0):
        shader = self._shaders[shader_id]
        assert shader is not None

        if type == 'param':
            shader.set_param(name, value)
        elif type == 'trans':
            shader.set_trans(name, value)
        elif type == 'render':
            shader.set_render(name, value)
        else:
            raise Exception("Unknow shader type %s" % type)

    # def get_shader_param(self, name, shader_id=0):
    #     shader = self._shaders[shader_id]
    #     assert shader is not None
    #
    #     return shader.get_param(name)

    # def  build_data(self, data):
    #     return ArrayDatatype.asArray(data, GL_1_1.GL_FLOAT)

    def build_vbo(self, rdata, vformat, vdivisor=None, att_st=0):

        vertices = ArrayDatatype.asArray(rdata, GL_1_1.GL_FLOAT)

        vbo_id = glGenBuffers(1)

        glBindBuffer(GL_ARRAY_BUFFER, vbo_id)
        glBufferData(GL_ARRAY_BUFFER, len(vertices) * sizeof(c_float), vertices, GL_STATIC_DRAW)

        stride = sum(vformat) * sizeof(c_float)
        for i, size in enumerate(vformat):
            att_id = i + att_st
            offset = sum(vformat[:i]) * sizeof(c_float)
            glVertexAttribPointer(att_id, size, GL_FLOAT, GL_FALSE,
                                  stride, c_void_p(offset))
            glEnableVertexAttribArray(att_id)
            if vdivisor:
                glVertexAttribDivisor(att_id, vdivisor[i])

        atts = len(vformat)
        count = int(len(rdata) / sum(vformat))
        return dict(id=vbo_id, rdata=rdata, vformat=vformat, att_st=att_st, atts=atts, count=count)

    def update_vbo(self, vbo, buf_t=GL_DYNAMIC_DRAW):
        #GL_STATIC_DRAW
        #GL_STREAM_DRAW
        #GL_DYNAMIC_DRAW

        rdata = vbo['rdata']
        vbo_id = vbo['id']
        vertices = ArrayDatatype.asArray(rdata, GL_1_1.GL_FLOAT)

        glBindBuffer(GL_ARRAY_BUFFER, vbo_id)
        glBufferData(GL_ARRAY_BUFFER, len(vertices) * sizeof(c_float), vertices, buf_t)

    def build_vao(self, datas):
        vao_id = glGenVertexArrays(1)
        glBindVertexArray(vao_id)  # VAO record start

        vbos = {}
        att_st = 0
        for name, rdata in datas.items():
            vbo = self.build_vbo(*rdata, att_st)
            att_st += vbo['atts']
            vbos[name] = vbo

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)  # VAO record end

        return dict(id=vao_id, vbos=vbos)

    def build_shader(self, vcode, fcode):
        #vertex shader
        vertexShaderSource = vcode.encode()
        vertexShader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertexShader, vertexShaderSource)
        glCompileShader(vertexShader)
        result = glGetShaderiv(vertexShader, GL_COMPILE_STATUS)
        if result == GL_FALSE:
            infoLog = glGetShaderInfoLog(vertexShader)
            print("vertex compile failed:", infoLog.decode('utf-8'))
            return
        else:
            print(vertexShaderSource, result)

        # fragment shader
        fragmentShaderSource = fcode.encode()
        fragmentShader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragmentShader, fragmentShaderSource)
        glCompileShader(fragmentShader)
        result = glGetShaderiv(fragmentShader, GL_COMPILE_STATUS)
        if result == GL_FALSE:
            infoLog = glGetShaderInfoLog(fragmentShader)
            print("fragment compile failed::", infoLog.decode('utf-8'))
            return
        else:
            print(fragmentShaderSource, result)

        #link shader
        shaderProgram = glCreateProgram()
        glAttachShader(shaderProgram, vertexShader)
        glAttachShader(shaderProgram, fragmentShader)
        glLinkProgram(shaderProgram)
        result = glGetProgramiv(shaderProgram, GL_LINK_STATUS)
        if result == GL_FALSE:
            infoLog = glGetProgramInfoLog(shaderProgram)
            print("program link error:", infoLog.decode('utf-8'))
            return
        else:
            print("linked", result)

        glDetachShader(shaderProgram, vertexShader)
        glDetachShader(shaderProgram, fragmentShader)
        glDeleteShader(vertexShader)
        glDeleteShader(fragmentShader)

        return shaderProgram

    def build_texture(self, source):
        if not source:
            return None

        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        # GL_REPEAT/GL_MIRRORED_REPEAT/GL_CLAMP_TO_EDGE/GL_CLAMP_TO_BORDER
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D,
                        GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,
                        GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        # glTexParameteri(GL_TEXTURE_2D,
        #                 GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)

        # load texture image
        pygame.init()
        # pygame.display.set_mode((w, h), pygame.DOUBLEBUF | pygame.OPENGL)
        img = pygame.image.load(source)
        if not img:
            return

        bitsize = img.get_bitsize()
        if bitsize == 32:
            src_format = 'RGBA'
            opg_format = GL_RGBA
        elif bitsize == 24:
            src_format = 'RGB'
            opg_format = GL_RGB
        else:
            print(self.__class__.__name__, "texture source not support", source, bitsize)
            return

        data = pygame.image.tostring(img, src_format, 1)
        img_width = img.get_width()
        img_height = img.get_height()
        out_format = GL_RGB
        glTexImage2D(GL_TEXTURE_2D, 0, out_format, img_width, img_height, 0, opg_format, GL_UNSIGNED_BYTE, data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)

        pygame.quit()

        return tex_id

    # def model_transform(self, shader):
    #     return glm.mat4(1)
    #     #self.store_id('model', model, shader_id)
    #
    # def view_transform(self, shader):
    #     return glm.mat4(1)
    #     #self.store_id('view', view, shader_id)
    #
    # def project_transform(self, shader):
    #     return glm.mat4(1)
    #     #self.store_id('project', proj, shader_id)
    #
    # def texture_transform(self, shader):
    #     tex = shader.get_param('texture')
    #     if tex is None:
    #         return
    #
    #     return tex

    def render_model(self, shader, model):
        # result = self.get_id(['program', 'model'], shader_id)
        # if not all(result):
        #     return
        #
        # program, model = result
        program = shader.get_param('program')
        glUniformMatrix4fv(glGetUniformLocation(program, "model"),
                           1, GL_FALSE, glm.value_ptr(model))

    def render_view(self, shader, view):
        # result = self.get_id(['program', 'view'], shader_id)
        # if not all(result):
        #     return
        #
        # program, view = result
        program = shader.get_param('program')
        glUniformMatrix4fv(glGetUniformLocation(program, 'view'),
                    1, GL_FALSE, glm.value_ptr(view))

    def render_proj(self, shader, project):
        # result = self.get_id(['program', 'project'], shader_id)
        # if not all(result):
        #     return
        #
        # program, project = result
        program = shader.get_param('program')
        glUniformMatrix4fv(glGetUniformLocation(program, 'projection'),
                           1, GL_FALSE, glm.value_ptr(project))

    def render_texture(self, shader, texture):
        # result = self.get_id(['program', 'texture'])
        # if not all(result):
        #     print(self.__class__.__name__, "render_texture vars empty", result)
        #     return
        #
        # program, tex = result

        program, texs= shader.get_param(['program', 'texs'])
        for i, tex in enumerate(texs):
            if tex:
                suffix = str(i)
                tag = globals()['GL_TEXTURE'+ suffix]   #GL_TEXTURE0 ...
                glActiveTexture(tag)
                glBindTexture(GL_TEXTURE_2D, tex)
                if i == 0:
                    suffix_f = ''
                else:
                    suffix_f = suffix
                t = glGetUniformLocation(program, "tex" + suffix_f) #tex, tex1, tex2 in program
                glUniform1i(t, i)  # 设置纹理单元为0号

    # def _render_start(self, shader):
    #     result = shader.get_param(['program', 'vao'])
    #     if not all(result):
    #         print(self.__class__.__name__, "_render_start var empty", result)
    #         return
    #
    #     program, vao_id = result
    #
    #     glBindVertexArray(vao_id)
    #     glUseProgram(program)

    # def _render_end(self, shader):
    #     result = self.get_shader_param(['vertices', 'vformat'])
    #     if not all(result):
    #         print(self.__class__.__name__, "_render_end var empty", result)
    #         return
    #
    #     vertices, vformat = result
    #
    #     # 使用索引绘制
    #     # glDrawElements(GL_TRIANGLES, len(indices), GL_UNSIGNED_SHORT, c_void_p(0))
    #     glDrawArrays(GL_TRIANGLES, 0, int(len(vertices) / sum(vformat)))

    def _render_start(self, shader):
        program, vao = shader.get_param(['program', 'vao'])
        vbos = vao['vbos']

        for name, vbo in vbos.items():
            result = shader.refresh(name, vbo)
            if result:
                self.update_vbo(vbo, GL_DYNAMIC_DRAW)

        glBindVertexArray(vao['id'])
        glUseProgram(program)

    def _render_end(self, shader):
        # 使用索引绘制
        vao = shader.get_param('vao')

        vbos = vao['vbos']
        verx = vbos.get('vertex')
        inst = vbos.get('inst')
        if not inst:
            dup_count = 0
        else:
            dup_count =inst['count']

        count = verx['count']

        if dup_count:
            glDrawArraysInstanced(GL_TRIANGLES, 0, count, dup_count)
        else:
            glDrawArrays(GL_TRIANGLES, 0, count)

    def render(self, shader):
        shader.do_render(self.event)

    def run(self):
        # Enable depth test
        glEnable(GL_DEPTH_TEST)
        # Accept fragment if it closer to the camera than the former one
        #glDepthFunc(GL_LESS)
        # Cull triangles which normal is not towards the camera
        #glEnable(GL_CULL_FACE)

        lastFrame = 0
        while not glfw.window_should_close(self.window):
            # Render here, e.g. using pyOpenGL
            glClearColor(0, 0, 0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            for shader in self._shaders:
                self.render(shader)

            # Swap front and back buffers
            glfw.swap_buffers(self.window)

            # Poll for and process events
            #glfw.poll_events()
            if self.event:
                currentFrame = glfw.get_time()
                deltaTime = currentFrame - lastFrame
                lastFrame = currentFrame

                # Poll for and process events
                glfw.poll_events()
                self.event.do_movement(deltaTime)
            else:
                glfw.poll_events()

            glBindVertexArray(0)
            glUseProgram(0)

        glfw.terminate()
