import bpy
import bmesh
import struct
import mathutils
import math
import os, sys
from bpy.props import *
from . constants import *
from . helpers import *
import numpy
from enum import IntEnum

class ChunkType(IntEnum):

	FORM = 0x4D524F46 # file root

	TGEO = 0x4F454754 # geometry object
	TGHD = 0x44484754 # geometry object header
	TGPT = 0x54504754 # geometry vertex data

	TGIH = 0x48494754 # geometry instance header
	TGIN = 0x4E494754 # geometry instance

	TMTB = 0x42544D54 # mesh material ids
	MATI = 0x4954414D # material

	TGFM = 0x4D464754 # mesh triangle array / triangle strip?
	TGFP = 0x50464754 # collision triangle array?

	TIDA = 0x41444954 # float array
	TGVP = 0x50564754 # vertex position array
	TGVN = 0x4E564754 # vertex normals array
	TGVC = 0x43564754 # vertex color
	TGVU = 0x55564754 # vertex uvs

	TIVU = 0x55564954 # vertex uv container
	TIVN = 0x4E564954 # vertex normal container
	TIVC = 0x43564954 # vertex color container

	TII8 = 0x38494954 # indices 8 bit. see (TIVN, TGVU, TIVC)
	TII6 = 0x36494954 # indices 16 bit. see (TIVN, TGVU, TIVC)

	TXRH = 0x48525854 # texture resource header
	TDDS = 0x53444454 # DDS image
	TXPR = 0x52505854 # XPR image
	TBMP = 0x504D4254 # BMP image
	TZMP = 0x504D5A54 # ZMP image?
	TTGA = 0x41475454 # TGA image

	TGTD = 0x44544754 # 
	TGPH = 0x48504754
	TGLO = 0x4F4C4754
	TGCI = 0x49434754
	TGFE = 0x45464754
	TGFN = 0x4E464754
	TGFR = 0x52464754
	TGFT = 0x54464754
	TXRC = 0x43525854
	TGIT = 0x54494754
	TIFN = 0x4E464954

	DIDF = 0x46444944
	GRID = 0x44495247
	DLEN = 0x4E454C44
	OFST = 0x5453464F
	CLEN = 0x4E454C43
	NAME = 0x454D414E
	ZFSD = 0x4453465A
	SDPT = 0x54504453
	SDTD = 0x44544453
	ZPVS = 0x5356505A
	PVSH = 0x48535650
	PVSO = 0x4F535650
	ZDYN = 0x4E59445A
	DDEF = 0x46454444
	DBDY = 0x59444244
	DCON = 0x4E4F4344
	DBNC = 0x434E4244
	MOBO = 0x4F424F4D
	ANIM = 0x4D494E41
	DEFI = 0x49464544
	AROT = 0x544F5241
	ATRA = 0x41525441
	ATRW = 0x57525441
	ASCA = 0x41435341
	ACBH = 0x48424341
	ACBD = 0x44424341
	ACB = 0x49424341
	ZFFD = 0x4446465A
	ZPEC = 0x4345505A
	ZPEO = 0x4F45505A
	ZPED = 0x4445505A
	WSMC = 0x434D5357
	WSMO = 0x4F4D5357
	SDRD = 0x44524453
	ZLIT = 0x54494C5A
	LITH = 0x4854494C
	LITO = 0x4F54494C

	# BMXXX
	ZLZO = 0x4F5A4C5A
	ZSCD = 0x4443535A
	ZSCR = 0x5243535A
	ZFPH = 0x4850465A
	ZFPD = 0x4450465A
	ZFPT = 0x5450465A

	@classmethod
	def isKnownChunkType(self, type):
		return any(type == item.value for item in self)

class ZiffChunk:
	def __init__(self):
		self.type = None
		self.size = -1
		self.data = ''
		self.chunks = []

	def __str__(self):
		return str(self.__class__) + ': ' + str(self.__dict__)

	def __repr__(self):
		return str(self.__dict__)

	def isEmpty(self):
		return (True if (self.chunkSize > 0) else False)

	def containsChunkOfType(self, type):
		for chunk in self.chunks:
			if chunk.type == type:
				return True
		else:
			return False

	def getChunkOfType(self, type):
		for chunk in self.chunks:
			if chunk.type == type:
				return chunk
		else:
			return None

	def getChunksOfType(self, type):
		chunks = []
		for chunk in self.chunks:
			if chunk.type == type:
				chunks.append(chunk)
		return chunks

	def readChunk(self, br):
		chunk_type_temp = br.u32()

		if ChunkType.isKnownChunkType(chunk_type_temp):
			self.type = ChunkType(chunk_type_temp)
			self.size = br.u32()
			chunk_start_offset = br.offset

			print('Reading {} Chunk at {}, Size {}'.format(str(self.type), str(chunk_start_offset - 8), str(self.size)))

			self.data = br.read('{}x'.format(str(self.size)))
			chunk_end_offset = br.offset

			br.offset = chunk_start_offset
			while br.offset < chunk_end_offset:

				if (br.offset + 4 > br.length):
					break

				child = ZiffChunk()
				if child.readChunk(br) is not None:
					self.chunks.append(child)
				else:
					br.offset = chunk_end_offset

			return self

		else:

			return None

	def readRoot(self, br):
		self.type = ChunkType(br.u32())
		self.size = br.u32()
		chunk_start_offset = br.offset

		print('Reading {} Root at {}, Size {}'.format(str(ChunkType(self.type)), str(chunk_start_offset - 8), str(self.size)))

		self.data = br.read('{}x'.format(str(self.size)))
		chunk_end_offset = br.offset

		br.offset = chunk_start_offset
		while br.offset < chunk_end_offset:

			if (br.offset + 4 > br.length):
				break

			child = ZiffChunk()
			if child.readChunk(br) is not None:
				self.chunks.append(child)

		return self

def import_zaxis_geo(filename, directory, context, operator):
	p = Printer(); p.on = True
	input_file = os.path.join(directory, filename)
	print(input_file)

	with open(input_file, 'rb') as inp:
		br = Reader(inp.read())

	root_node_geo = ZiffChunk().readRoot(br)

#	with open('{}_DUMP.txt'.format(os.path.join(directory, filename.split('.')[0]).upper()), 'w') as outp:
#		outp.write(str(root_node))

class ZAxisToScene(bpy.types.Operator):
	bl_idname = 'io.zazis_to_scene'
	bl_label = 'ZAxis Scene (.GEO)'

	filter_glob = StringProperty(default='*.geo', options={'HIDDEN'})
	filename = StringProperty(name='File Name')
	directory = StringProperty(name='Directory')
#	load_tex = BoolProperty(name='Load textures', default=True)

	def execute(self, context):
		filename = self.filename
		directory = self.directory

		import_zaxis_geo(filename, directory, context, self)

		return {'FINISHED'}

	def invoke(self, context, event):
		wm = bpy.context.window_manager
		wm.fileselect_add(self)

		return {'RUNNING_MODAL'}