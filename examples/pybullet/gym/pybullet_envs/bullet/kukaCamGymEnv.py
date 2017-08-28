import os, inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
print ("current_dir=" + currentdir)
os.sys.path.insert(0,currentdir)

import math
import gym
from gym import spaces
from gym.utils import seeding
import numpy as np
import time
import pybullet as p
from . import kuka
import random
import pybullet_data


class KukaCamGymEnv(gym.Env):
  metadata = {
      'render.modes': ['human', 'rgb_array'],
      'video.frames_per_second' : 50
  }

  def __init__(self,
               urdfRoot=pybullet_data.getDataPath(),
               actionRepeat=1,
               isEnableSelfCollision=True,
               renders=True):
    print("init")
    self._timeStep = 1./240.
    self._urdfRoot = urdfRoot
    self._actionRepeat = actionRepeat
    self._isEnableSelfCollision = isEnableSelfCollision
    self._observation = []
    self._envStepCounter = 0
    self._renders = renders
    self._width = 341
    self._height = 256
    self.terminated = 0
    self._p = p
    if self._renders:
      p.connect(p.GUI)
      p.resetDebugVisualizerCamera(1.3,180,-41,[0.52,-0.2,-0.33])
    else:
      p.connect(p.DIRECT)
    #timinglog = p.startStateLogging(p.STATE_LOGGING_PROFILE_TIMINGS, "kukaTimings.json")
    self._seed()
    self.reset()
    observationDim = len(self.getExtendedObservation())
    #print("observationDim")
    #print(observationDim)
    
    observation_high = np.array([np.finfo(np.float32).max] * observationDim)    
    self.action_space = spaces.Discrete(7)
    self.observation_space = spaces.Box(low=0, high=255, shape=(self._height, self._width, 4))
    self.viewer = None

  def _reset(self):
    print("reset")
    self.terminated = 0
    p.resetSimulation()
    p.setPhysicsEngineParameter(numSolverIterations=150)
    p.setTimeStep(self._timeStep)
    p.loadURDF(os.path.join(self._urdfRoot,"plane.urdf"),[0,0,-1])
    
    p.loadURDF(os.path.join(self._urdfRoot,"table/table.urdf"), 0.5000000,0.00000,-.820000,0.000000,0.000000,0.0,1.0)
    
    xpos = 0.5 +0.05*random.random()
    ypos = 0 +0.05*random.random()
    ang = 3.1415925438*random.random()
    orn = p.getQuaternionFromEuler([0,0,ang])
    self.blockUid =p.loadURDF(os.path.join(self._urdfRoot,"block.urdf"), xpos,ypos,-0.1,orn[0],orn[1],orn[2],orn[3])
            
    p.setGravity(0,0,-10)
    self._kuka = kuka.Kuka(urdfRootPath=self._urdfRoot, timeStep=self._timeStep)
    self._envStepCounter = 0
    p.stepSimulation()
    self._observation = self.getExtendedObservation()
    return np.array(self._observation)

  def __del__(self):
    p.disconnect()

  def _seed(self, seed=None):
    self.np_random, seed = seeding.np_random(seed)
    return [seed]

  def getExtendedObservation(self):
     
     #camEyePos = [0.03,0.236,0.54]
     #distance = 1.06
     #pitch=-56
     #yaw = 258
     #roll=0
     #upAxisIndex = 2
     #camInfo = p.getDebugVisualizerCamera()
     #print("width,height")
     #print(camInfo[0])
     #print(camInfo[1])
     #print("viewMatrix")
     #print(camInfo[2])
     #print("projectionMatrix")
     #print(camInfo[3])
     #viewMat = camInfo[2]
     #viewMat = p.computeViewMatrixFromYawPitchRoll(camEyePos,distance,yaw, pitch,roll,upAxisIndex)
     viewMat = [-0.5120397806167603, 0.7171027660369873, -0.47284144163131714, 0.0, -0.8589617609977722, -0.42747554183006287, 0.28186774253845215, 0.0, 0.0, 0.5504802465438843, 0.8348482847213745, 0.0, 0.1925382763147354, -0.24935829639434814, -0.4401884973049164, 1.0]
     #projMatrix = camInfo[3]#[0.7499999403953552, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0000200271606445, -1.0, 0.0, 0.0, -0.02000020071864128, 0.0]
     projMatrix = [0.75, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0000200271606445, -1.0, 0.0, 0.0, -0.02000020071864128, 0.0]
     
     img_arr = p.getCameraImage(width=self._width,height=self._height,viewMatrix=viewMat,projectionMatrix=projMatrix)
     rgb=img_arr[2]
     np_img_arr = np.reshape(rgb, (self._height, self._width, 4))
     self._observation = np_img_arr
     return self._observation
  
  def _step(self, action):
    dv = 0.01
    dx = [0,-dv,dv,0,0,0,0][action]
    dy = [0,0,0,-dv,dv,0,0][action]
    da = [0,0,0,0,0,-0.1,0.1][action]
    f = 0.3
    realAction = [dx,dy,-0.002,da,f]
    return self.step2( realAction)
     
  def step2(self, action):
    self._kuka.applyAction(action)
    for i in range(self._actionRepeat):
      p.stepSimulation()
      if self._renders:
        time.sleep(self._timeStep)
      self._observation = self.getExtendedObservation()
      if self._termination():
        break
      self._envStepCounter += 1
    #print("self._envStepCounter")
    #print(self._envStepCounter)
    
    done = self._termination()
    reward = self._reward()
    #print("len=%r" % len(self._observation))
    
    return np.array(self._observation), reward, done, {}

  def _render(self, mode='human', close=False):
      return

  def _termination(self):
    #print (self._kuka.endEffectorPos[2])
    state = p.getLinkState(self._kuka.kukaUid,self._kuka.kukaEndEffectorIndex)
    actualEndEffectorPos = state[0]
      
    #print("self._envStepCounter")
    #print(self._envStepCounter)
    if (self.terminated or self._envStepCounter>1000):
      self._observation = self.getExtendedObservation()
      return True
    
    if (actualEndEffectorPos[2] <= 0.10):
      self.terminated = 1
      
      #print("closing gripper, attempting grasp")
      #start grasp and terminate
      fingerAngle = 0.3
      
      for i in range (1000):
        graspAction = [0,0,0.001,0,fingerAngle]
        self._kuka.applyAction(graspAction)
        p.stepSimulation()
        fingerAngle = fingerAngle-(0.3/100.)
        if (fingerAngle<0):
          fingerAngle=0
        
      self._observation = self.getExtendedObservation()
      return True
    return False
    
  def _reward(self):
    
    #rewards is height of target object
    blockPos,blockOrn=p.getBasePositionAndOrientation(self.blockUid)
    closestPoints = p.getClosestPoints(self.blockUid,self._kuka.kukaUid,1000) 

    reward = -1000    
    numPt = len(closestPoints)
    #print(numPt)
    if (numPt>0):
      #print("reward:")
      reward = -closestPoints[0][8]*10

    if (blockPos[2] >0.2):
      print("grasped a block!!!")
      print("self._envStepCounter")
      print(self._envStepCounter)
      reward = reward+1000

    #print("reward")
    #print(reward)
    return reward
