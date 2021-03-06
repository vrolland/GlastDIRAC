#!/bin/env python
""" Install software in Software Area 

Created 06/07/2013
@author: V. Rolland (IN2P3/LUPM)

"""
import os, shutil
from DIRAC import S_OK, S_ERROR


def getArrayFromTag(tag):
  """ Returns a dictionary containing the software inforamtions from the tag name
  """
  #tags are VO.glast.org-OS/FLAOUR/TAG, and in the SW dir it's the same
  infosoft = {}
  tag = tag.replace("VO-glast.org-","")
  items = tag.split("/")
  if len(items)!=4:
    return S_ERROR("Bad tag structure")
  
  infosoft["os"]= items[0]
  infosoft["variant"]= items[1]
  infosoft["package"]= items[2]
  infosoft["version"]= items[3]

  return S_OK(infosoft)



def InstallSoftware(tag, verbose=True):
  """ Look into the shared area and report back to the SoftwareTag service
  """
  from DIRAC import gLogger,gConfig

  if not 'VO_GLAST_ORG_SW_DIR' in os.environ:
    return S_ERROR("Missing VO_GLAST_ORG_SW_DIR environment variable")

  base_sw_dir = os.environ['VO_GLAST_ORG_SW_DIR']
  
  from GlastDIRAC.ResourceStatusSystem.Client.SoftwareTagClient import SoftwareTagClient
  swtc = SoftwareTagClient()

  
  gLogger.notice("Found the following software directory:", base_sw_dir)
  message = None
  

  from DIRAC.ConfigurationSystem.Client.Helpers.Operations    import Operations
  op = Operations('glast.org')
  rsync_server = op.getValue( "Pipeline/RsyncServer", "ccglast02.in2p3.fr::VO_GLAST_ORG_SW_DIR" )
  #rsync_server = "ccglast02.in2p3.fr::VO_GLAST_ORG_SW_DIR"
  rsync_cmd = "/usr/bin/rsync -az"
  
  # tag parsing
  res = getArrayFromTag(tag)
  if not res['OK']:
    return S_ERROR(res['Message'])  

  infosoft = res['Value']  
  OS_GLEAM = infosoft['os']
  VERSION_GLEAM = infosoft['version']
  VARIANT_GLEAM = infosoft['variant']
  SW_SHARED_DIR = base_sw_dir+"/glast/"
  
  
  # Directories to install ###########################################################################################
  dir_to_install = {} # name => ['src','destination']
  dir_to_install['setup script'] = ['/setup.sh', "/"]
  dir_to_install['Moot files'] = ['/moot/', "/moot/"]
  dir_to_install['Missing librairies'] = ['/lib/'+OS_GLEAM+"/", "/lib/"+OS_GLEAM+"/"]
  dir_to_install['Calibrations files'] = ['/ground/releases/calibrations/', "/ground/releases/calibrations/"]
  dir_to_install['GLAST_EXT'] = ["/ground/GLAST_EXT/"+OS_GLEAM+"/", "/ground/GLAST_EXT/"+OS_GLEAM+"/"]
  dir_to_install['Gleam'] = ["/ground/releases/"+OS_GLEAM+"/"+VARIANT_GLEAM+"/GlastRelease/"+VERSION_GLEAM+"/", "/ground/releases/"+OS_GLEAM+"/"+VARIANT_GLEAM+"/GlastRelease/"+VERSION_GLEAM+"/"]
  dir_to_install['GPL librairie files'] = ["/ground/PipelineConfig/", "/ground/PipelineConfig/"]
  dir_to_install['Overlay data files'] = ["/overlay-data/", "/overlay-data/"]
  dir_to_install['Overlay XML files'] = ["/overlay/", "/overlay/"]
  dir_to_install['Transfer wilko files'] = ["/transferwilko/", "/transferwilko/"]
  
  
  if verbose:
    rsync_cmd = rsync_cmd+"v" # add the parameter "verbose" to the command line
  rsync_cmd = rsync_cmd + " " + rsync_server
    
  for name,array in dir_to_install.iteritems():
    if not os.path.isdir( SW_SHARED_DIR+array[1] ):
      os.makedirs ( SW_SHARED_DIR+array[1] )
        
    gLogger.notice(" '"+name+"' retrieval with '"+rsync_cmd+array[0]+" "+SW_SHARED_DIR+array[1]+"'")
    gLogger.notice(" ... ")
    if os.system(rsync_cmd+array[0]+" "+SW_SHARED_DIR+array[1]) != 0 :
      gLogger.notice(" -> FAILED !")
      gLogger.error("*** Error during the retrieval of '"+array[1]+"' from '"+rsync_server+"'")
      if os.path.isdir( SW_SHARED_DIR+array[1] ):
          shutil.rmtree(SW_SHARED_DIR+array[1]);
      return S_ERROR("Error during the retrieval of '"+array[1]+"' from '"+rsync_server+"'")
    gLogger.notice(" -> OK !")  
  
  
    site = gConfig.getValue('/LocalSite/Site','')
    if site == '':
        return S_ERROR("Fail to retrieve the site name")
        
    res = swtc.updateStatus(tag,site,"Valid")
    if not res['OK']:
        return S_ERROR('Message: %s'%res['Message'])
    elif res['Value']['Failed']:
        return S_ERROR('Failed to update %s'%res['Value']['Failed'])
    else:
        return S_ERROR('Successfully updated %i CEs'%len(res['Value']['Successful']))
    return
  
  return S_OK()




if __name__ == '__main__':
    from DIRAC.Core.Base import Script
    
    from DIRAC import gLogger, exit as dexit
    
    verbose = False
    Script.registerSwitch( "v", "verbose", "Turn verbose on"  )
    Script.setUsageMessage( '\n'.join( [ __doc__.split( '\n' )[1],
                                       'Usage:',
                                       '  %s [option|cfgfile] ... TAG ...' % Script.scriptName,
                                       'Arguments:',
                                       '  TAG:      Software tag you want to install' ] ) )
    Script.parseCommandLine()
    for switch in Script.getUnprocessedSwitches():
      if switch[0] == "v" or switch[0].lower() == "verbose":
        verbose =  True
    
    args = Script.getPositionalArgs()
    
    if len( args ) != 1:
        Script.showHelp()

    res = InstallSoftware(args[0],verbose)
    if not res['OK']:
      gLogger.error(res['Message'])
      dexit(1)
    
    dexit(0)
    
