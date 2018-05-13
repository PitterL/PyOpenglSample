from OpenGL.GL import *
from OpenGL.GL import shaders
# from OpenGL.extensions import GLQuerier
import glfw
import pygame
import glm
import math
import numpy
from ctypes import sizeof, c_float, c_void_p, c_uint, c_short

from OpenGL import arrays
from OpenGL.arrays.arraydatatype import GLfloatArray
from OpenGL.GL.VERSION import GL_1_1
from math import *
from opg_wrapper import OpenglWrapper, ShaderData
from tools import CData
from objloader import ObjFile


class Camera(object):
    #定义移动方向
    (FORWARD, BACKWARD, LEFT, RIGHT) = range(4)

    #定义预设常量
    YAW = 0.0
    PITCH = 0.0
    SPEED = 3.0
    MOUSE_SENSITIVTY = 0.05
    MOUSE_ZOOM = 45.0
    MAX_PITCH_ANGLE = 89.0 # 防止万向锁

    def __init__(self, pos=glm.vec3(0.0, 0.0, 2.0), up=glm.vec3(0.0, 1.0, 0.0), yaw=YAW, pitch=PITCH):
        self.position = pos
        self.forward = glm.vec3(0.0, 0.0, -1.0)
        self.side = glm.vec3(-1, 0, 0)
        self.viewUp = up
        self.moveSpeed = self.SPEED
        self.mouse_zoom = self.MOUSE_ZOOM
        self.mouse_sensitivity = self.MOUSE_SENSITIVTY
        self.yawAngle = yaw
        self.pitchAngle = pitch


    def getViewMatrix(self):
        return glm.lookAt(self.position, self.position + self.forward, self.viewUp)

    #处理键盘按键后方向移动
    def handleKeyPress(self, dir, deltaTime):
        velocity = self.moveSpeed * deltaTime
        if dir == self.FORWARD:
            self.position += self.forward * velocity
        elif dir == self.BACKWARD:
            self.position -= self.forward * velocity
        elif dir == self.LEFT:
            self.position -= self.side * velocity
        elif dir == self.RIGHT:
            self.position += self.side * velocity

    #处理鼠标移动
    def handleMouseMove(self, xoffset, yoffset):
        yoffset = -yoffset

        xoffset *= self.mouse_sensitivity; # 用鼠标灵敏度调节角度变换
        yoffset *= self.mouse_sensitivity

        self.yawAngle += xoffset
        self.pitchAngle += yoffset

        self.normalizeAngle()
        self.updateCameraVectors()

    # 处理鼠标滚轮缩放 保持在[1.0, MOUSE_ZOOM]之间
    def handleMouseScroll(self, yoffset):
        if self.mouse_zoom >= 1.0 and self.mouse_zoom <= self.MOUSE_ZOOM:
            self.mouse_zoom -= self.mouse_sensitivity * yoffset;

        if self.mouse_zoom <= 1.0:
            self.mouse_zoom = 1.0

        if self.mouse_zoom >= 45.0:
            self.mouse_zoom = 45.0

    # 使pitch yaw角度保持在合理范围内
    def normalizeAngle(self):
        if self.pitchAngle > self.MAX_PITCH_ANGLE:
            self.pitchAngle = self.MAX_PITCH_ANGLE
        if self.pitchAngle < -self.MAX_PITCH_ANGLE:
            self.pitchAngle = -self.MAX_PITCH_ANGLE
        if self.yawAngle < 0.0:
            self.yawAngle += 360.0

    # 计算forward side向量
    def updateCameraVectors(self):
        forward = glm.vec3()
        forward.x = -sin(glm.radians(self.yawAngle)) * cos(glm.radians(self.pitchAngle))
        forward.y = -sin(glm.radians(self.pitchAngle))
        forward.z = -cos(glm.radians(self.yawAngle)) * cos(glm.radians(self.pitchAngle))
        self.forward = glm.normalize(forward)

        side = glm.vec3()
        side.x = cos(glm.radians(self.yawAngle))
        side.y = 0
        side.z = -sin(glm.radians(self.yawAngle))
        self.side = glm.normalize(side)

class WindowEvent(object):
    CAMERA_POS = glm.vec3(0.0, 0.0, 2.0)

    class Point(object):
        def __init__(self):
            self.x = 0
            self.y = 0
            self.inited = False

        def update(self, x, y):
            offfset = (x - self.x, y - self.y)
            self.x = x
            self.y = y

            return offfset

        def valid(self):
            return self.inited

        def release(self):
            self.x = self.y = 0
            self.inited = False

    def __init__(self, w, h):
        self.last = self.Point()
        self.camera = Camera(pos=self.CAMERA_POS)
        self.key_status = {}
        self.window_size = (w, h)

    def key_callback(self, window, key, scancode, action, mode):
        # 当用户按下ESC, 我们就把WindowShouldClose设置为true, 关闭应用
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, GL_TRUE);
        else:
            if action == glfw.PRESS:
                if key in self.key_status.keys():
                    self.key_status[key] = True
                else:
                    self.key_status[key] = False
            else:
                self.key_status.pop(key, None)

    def mouse_move_callback(self, window, xpos, ypos):
        # 首次鼠标移动
        offset = self.last.update(xpos, ypos)
        self.camera.handleMouseMove(*offset)

    # 由相机辅助类处理鼠标滚轮控制
    def mouse_scroll_callback(self, window, xoffset, yoffset):
        self.camera.handleMouseScroll(yoffset)

    #由相机辅助类处理键盘控制
    def do_movement(self, deltaTime):
        if glfw.KEY_W in self.key_status.keys():
            self.camera.handleKeyPress(self.camera.FORWARD, deltaTime)

        if glfw.KEY_S in self.key_status.keys():
            self.camera.handleKeyPress(self.camera.BACKWARD, deltaTime)

        if glfw.KEY_A in self.key_status.keys():
            self.camera.handleKeyPress(self.camera.LEFT, deltaTime)

        if glfw.KEY_D in self.key_status.keys():
            self.camera.handleKeyPress(self.camera.RIGHT, deltaTime)

class lightShader(ShaderData):
    def __init__(self, **kwargs):
        super(lightShader, self).__init__(**kwargs)

        self.trans = glm.vec3(0, 0, 0)
        self.scale = glm.vec3(0.3)

    def refresh(self, name, vbo):
        if name == 'inst':
            data = vbo['rdata']
            radius = 2
            (xpos, ypos, zpos) = (0, 0, 0)
            xpos = radius * cos(glfw.get_time())
            ypos = radius * sin(glfw.get_time())
            #zpos = radius * sin(glfw.get_time())

            data[0] = xpos
            data[1] = ypos
            #print(data[0], data[1])

            return True

    def model_transform(self, event):
        model = glm.mat4(1)
        model = glm.translate(model, self.trans)
        #model = glm.rotate(model, glm.radians(80.0), glm.vec3(0, 1, 0))
        #model = glm.rotate(model, glfw.get_time(), glm.vec3(0, 1, 0))
        model = glm.scale(model, self.scale)
        return model

    def view_transform(self, event):
        if event:
            return event.camera.getViewMatrix()

        #return super(lightShader, self).view_transform(event)

        radius = 0.5
        (xpos, ypos, zpos) = (0, 0, 0)
        xpos = radius * cos(glfw.get_time())
        #ypos = radius * sin(glfw.get_time())
        zpos = radius * sin(glfw.get_time())

        # theta = glfw.get_time()
        # phi = glfw.get_time() / 2.0
        # xpos = radius * sin(theta) * cos(phi)
        # ypos = radius * sin(theta) * sin(phi)
        # zpos = radius * cos(theta)

        eye = glm.vec3(xpos, ypos, zpos)
        center = glm.vec3(0)
        up = glm.vec3(0, 1, 0)

        # radius = 1
        # xpos = radius * math.cos(glfw.get_time())
        # # ypos = radius * math.sin(glfw.get_time())
        # ypos = 0
        # zpos = radius * math.sin(glfw.get_time())
        # eye = glm.vec3(xpos, ypos, zpos)
        # center = glm.vec3()
        # up = glm.vec3(0, 1, 0)

        view = glm.lookAt(eye, center, up)
        #self.store_id('view', view, shader_id)
        return view

    def project_transform(self, event):
        # parent = shader.get_param('parent')
        # if not parent:
        #     return super(lightShader, self).project_transform(shader)
        #
        # w, h = parent.window_size
        # proj = glm.perspective(glm.radians(45), w / h, 1, 100)
        # #self.store_id('project', proj, shader_id)
        # return proj

        if event:
            w, h = event.window_size
            return glm.perspective(event.camera.mouse_zoom, w / h, 1, 100)

        return super(lightShader, self).project_transform(event)

class LightBasic(OpenglWrapper):
    def __init__(self, **kwargs):
        super(LightBasic, self).__init__(**kwargs)
        #self.light_pos = None

    # def create_window(self, w, h, event):
    #     super(LightBasic, self).create_window(w, h, event)

    # def _render_start(self, shader):
    #     super(LightBasic, self)._render_start(shader)
    #
    #     lamp_pos = glm.vec3(0, 0, 0)
    #     radius = 0.5
    #     #lamp_pos.x = radius * cos(glfw.get_time()/2)
    #     lamp_pos.y = radius * cos(glfw.get_time()/2)
    #     lamp_pos.z = radius * sin(glfw.get_time()/2)
    #
    #     program = shader.get_param('program')
    #     if isinstance(shader, lightShader):
    #         # pos = glGetUniformLocation(program, 'gl_pos')
    #         # print(pos)
    #         shader.trans = lamp_pos

def main():
    # light
    vcode = """
        #version 330

        layout (location = 0) in vec3 position;
        layout (location = 1) in vec3 color;
        layout (location = 2) in vec2 text;
        layout (location = 3) in vec3 offset;

        out vec3 ver_color;
        out vec2 ver_tex;

        uniform mat4 projection;
        uniform mat4 view;
        uniform mat4 model;

        void main()
        {{
            gl_Position = projection * view * model * vec4(position + offset, 1.0);
            ver_color = color;
            ver_tex = text;
        }}"""

    fcode = """
        #version 330
        in vec3 ver_color;
        in vec2 ver_tex;
        out vec4 color;
        uniform sampler2D tex;

        void main()
        {{
            color = vec4(ver_color, 1.0f);
            //color = texture(tex, ver_tex);
        }}"""

    scene = ObjFile("3Drendering\monkey.obj")
    m = list(scene.objects.values())[0]
    data = m.vertices
    vformat = list(zip(*m.vertex_format))[1]

    data_a = (
        -0.5, -0.5, 0.5, 0.0, 0.0, 1.0, 0.0, 0.0,   # A
        0.5, -0.5, 0.5, 0.0, 1.0, 0.0, 1.0, 0.0,    # B
        0.5, 0.5, 0.5, 0.0, 1.0, 1.0, 1.0, 1.0,     # C
        -0.5, 0.5, 0.5, 1.0, 0.0, 0.0, 0.0, 1.0,    # D
        -0.5, -0.5, -0.5, 1.0, 0.0, 1.0, 0.0, 0.0,  # E
        0.5, -0.5, -0.5, 1.0, 1.0, 0.0, 1.0, 0.0,   # F
        0.5, 0.5, -0.5, 1.0, 1.0, 1.0, 1.0, 1.0,    # G
        -0.5, 0.5, -0.5, 0.0, 0.0, 0.0, 0.0, 1.0,    # H
    )
    data_i = (
        0, 1, 2, 2, 3, 0 ,
        4, 7, 6, 6, 5, 4,
        3, 7, 4, 4, 0, 3,
        5, 6, 2, 2, 1, 5,
        6, 7, 3, 3, 2, 6,
        0, 4, 5, 5, 1, 0,
    )

    vformat1 = [3, 3, 2]
    data1 = []
    size_point = sum(vformat1)
    for i in data_i:
        data1.extend(data_a[i * size_point: (i + 1) * size_point])

    tdata = []
    for x in range(-2, 2, 2):
        for y in range(-2, 2, 2):
            tdata.extend([x, y, 0])
    tformat = [3]
    tdivisor = [1]

    light = LightBasic()
    w, h = 800, 480
    event = WindowEvent(w, h)
    #event = None
    light.create_window(w, h, event)

    vex_data = (data1, vformat1, None)
    inst_data = (tdata, tformat, tdivisor)

    datas = {'vertex': vex_data, 'inst': inst_data}

    shader = light.create_shader_instances(datas, vcode, fcode, "wood.png", lightShader)
    if shader is None:
        print("create shader failed")
        return

    # light.set_shader('trans', 'view', light.box_view_transform, shader_box)
    # light.set_shader('trans', 'project', light.box_project_transform, shader_box)

    light.run()

if __name__ == "__main__":
    main()