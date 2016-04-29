#=============================================================================
## Automatic Repository Version Generation Utility
## Author: Zhenyu Wu
## Revision 1: Apr 28. 2016 - Initial Implementation
#=============================================================================

import sys

class GitProject:
	RepoTokens = type('Tokens', (object,), {
		'prefix': '?',
		'major': -1,
		'minor': -1,
		'commits': -1,
		'hashcode': '?',
		'branch': '?',
		'state': '?'
	})
	ReleaseBranch = None
	ReleaseTagged = None
	Modifications = None
	
	class ModTracker:
		name = None
                untracked = -1
                unstaged =  -1
                uncommitted =  -1
		submodules = None
		
		def __init__(self, repo, name):
			self.name = name
			self.untracked = len(repo.untracked_files)
			self.unstaged = len(repo.index.diff(None))
			self.uncommitted = len(repo.index.diff('HEAD'))
			
			self.submodules = []
			for submodule in repo.submodules:
				submod = self.__class__(submodule.module(), submodule.name)
				if submod.isDirty():
					self.unstaged-= 1
					self.submodules.append(submod)
		
		def isDirty(self):
			return self.untracked+self.unstaged+self.uncommitted+len(self.submodules) > 0
	
	def __init__(self, rootdir, relbranchpfx='rel-', accepttagpfx = ('v','m')):
		for pfx in accepttagpfx:
			if len(pfx) != 1:
				raise Exception("Invalid tag prefix '%s'"%pfx)
		reltagpfx = accepttagpfx[0]
		
		from git import Repo
		repo = Repo(rootdir)
		
		BRANCH = repo.active_branch.name
		self.RepoTokens.branch = BRANCH
		self.ReleaseBranch = BRANCH.startswith(relbranchpfx)
		
		DESC = repo.git.describe('--long')
		self.RepoTokens.prefix = None
		for pfx in accepttagpfx:
			if DESC.startswith(pfx):
				self.RepoTokens.prefix = pfx
		if self.RepoTokens.prefix is None:
			raise Exception("Tag '%s' with unacceptable prefix"%DESC)
		self.ReleaseTagged = self.RepoTokens.prefix == reltagpfx
		
		import re
		desctokens = re.match('(\d+)\\.(\d+)\\-(\d+)\\-g(.*)', DESC[len(pfx):])
		if desctokens is None:
			raise Exception("Malformed tag content '%s'"%DESC)
		
		self.RepoTokens.major = int(desctokens.group(1))
		self.RepoTokens.minor = int(desctokens.group(2))
		self.RepoTokens.commits = int(desctokens.group(3))
		self.RepoTokens.hashcode = desctokens.group(4)
		
		self.Modifications = self.ModTracker(repo,'.')
		
		self.RepoTokens.state = 'dirty' if self.Modifications.isDirty() else None
	
	def isDangerous(self):
		return self.Modifications.isDirty()
	
	def isSane(self):
		return (self.ReleaseBranch and self.ReleaseTagged and not self.isDangerous()) or not self.ReleaseBranch
	
	def getVersionString(self):
		Qualifier = self.RepoTokens.branch
		if not self.ReleaseTagged:
			Qualifier+= '.' + self.RepoTokens.prefix
		if self.RepoTokens.state is not None:
			Qualifier+= '.' + self.RepoTokens.state
		return "%d.%d.%d-%s"%(self.RepoTokens.major,self.RepoTokens.minor,self.RepoTokens.commits,Qualifier)
	
	def getQualifierFlags(self):
		flags = 0
		if not self.ReleaseBranch:
			flags|= 0x01
		if not self.ReleaseTagged:
			flags|= 0x02
		if self.Modifications.isDirty():
			flags|= 0x08
			if self.Modifications.untracked > 0:
				flags|= 0x10
			if self.Modifications.unstaged > 0:
				flags|= 0x20
			if self.Modifications.uncommitted > 0:
				flags|= 0x40
			if len(self.Modifications.submodules) > 0:
				flags|= 0x80
		return flags
	
	def getNumericalVersion(self):
		return (self.RepoTokens.major,self.RepoTokens.minor,self.RepoTokens.commits,self.getQualifierFlags())
	
	def explainQualifierFlags(self, flags):
		if flags & 0xFB != flags:
			raise Exception("Invalid qualifier flag (0x%X)"%flags)
		
		ret = []
		ret.append('Non-release branch' if flags & 0x01 else 'Release branch')
		ret.append('Non-release tagged' if flags & 0x02 else 'Release tagged')
		
		if flags & 0x08:
			ret.append('Source Dirty')
			if flags & 0xF0 == 0:
				raise Exception("Invalid qualifier flag. expect dirty flags (0x%X)"%flags)
			
			if flags & 0x10:
				ret.append('Untracked')
			if flags & 0x20:
				ret.append('Unstaged')
			if flags & 0x40:
				ret.append('Uncommited')
			if flags & 0x80:
				ret.append('Submodule')
		else:
			if flags & 0xF0 != 0:
				raise Exception("Invalid qualifier flag. unexpected dirty flags (0x%X)"%flags)
		
		return ret
	
	def getMavenVersionString(self):
		if not self.isSane():
			raise Exception("Insane version configuration")
		
		if self.ReleaseBranch:
			return self.getVersionString()
		else:
			MinorVer = self.RepoTokens.minor if not self.ReleaseTagged else self.RepoTokens.minor+1
			return "%d.%d-SNAPSHOT"%(self.RepoTokens.major,MinorVer)

if __name__ == "__main__":
	try:
		Proj = GitProject('.')
		
		SHOW_VER = 'Ver'
		SHOW_NUMVER = 'NumVer'
		SHOW_MVNVER = 'MvnVer'
		SHOW_FLAGS = 'Flags'
		SHOW_DIRT = 'Dirt'
		
		ops = sys.argv[1:] if len(sys.argv) > 1 else (SHOW_VER,SHOW_FLAGS)
		
		for op in ops:
			if op.upper() == SHOW_VER.upper():
				print Proj.getVersionString()
			elif op.upper() == SHOW_NUMVER.upper():
				print '.'.join(str(x) for x in Proj.getNumericalVersion())
			elif op.upper() == SHOW_MVNVER.upper():
				print Proj.getMavenVersionString()
			elif op.upper() == SHOW_FLAGS.upper():
				print Proj.explainQualifierFlags(Proj.getQualifierFlags())
			elif op.upper() == SHOW_DIRT.upper():
				def PrintMods(mod,level=0):
					if mod.untracked:
						print "%s%d untracked files"%(' '*level,mod.untracked)
					if mod.unstaged:
						print "%s%d unstaged changes"%(' '*level,mod.unstaged)
					if mod.uncommitted:
						print "%s%d uncommitted changes"%(' '*level,mod.uncommitted)
					for submod in mod.submodules:
						print "%sSubmodule '%s':"%(' '*level,submod.name)
						PrintMods(submod,level+1)
				
				PrintMods(Proj.Modifications)
			else:
				raise Exception("Unknown request '%s'"%op)
	except Exception as e:
		print >>sys.stderr, "Error: %s"%str(e)
		#import traceback
		#traceback.print_exc()
		sys.exit(-1)

