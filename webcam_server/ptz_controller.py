from onvif import ONVIFCamera
import zeep
import logging

logger = logging.getLogger(__name__)

def zeep_pythonvalue(self, xmlvalue):
    return xmlvalue

zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue

class PTZController:
    def __init__(self, host, username, password):
        try:
            self.camera = ONVIFCamera(host, 
                                    port=80,
                                    user=username,
                                    passwd=password)
            
            # Create media service object
            self.media = self.camera.create_media_service()
            
            # Create ptz service object
            self.ptz = self.camera.create_ptz_service()

            # Get target profile
            media_profile = self.media.GetProfiles()[0]
            self.media_profile = media_profile.token

            # Get PTZ configuration options for getting continuous move range
            self.request = self.ptz.create_type('GetConfigurationOptions')
            self.request.ConfigurationToken = self.ptz.GetConfigurations()[0].token
            self.ptz_configuration_options = self.ptz.GetConfigurationOptions(self.request)

            logger.info("PTZ Controller initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PTZ controller: {str(e)}")
            raise

    def move_continuous(self, pan, tilt, zoom):
        """
        Continuous PTZ movement
        :param pan: Pan speed (-1.0 to 1.0)
        :param tilt: Tilt speed (-1.0 to 1.0)
        :param zoom: Zoom speed (-1.0 to 1.0)
        """
        try:
            request = self.ptz.create_type('ContinuousMove')
            request.ProfileToken = self.media_profile
            request.Velocity = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': zoom}
            self.ptz.ContinuousMove(request)
            logger.info(f"Continuous move: pan={pan}, tilt={tilt}, zoom={zoom}")
        except Exception as e:
            logger.error(f"Failed to execute continuous move: {str(e)}")
            raise

    def stop(self):
        """Stop all PTZ movements"""
        try:
            self.ptz.Stop({'ProfileToken': self.media_profile})
            logger.info("PTZ movement stopped")
        except Exception as e:
            logger.error(f"Failed to stop PTZ movement: {str(e)}")
            raise

    def move_absolute(self, pan, tilt, zoom):
        """
        Move to absolute position
        :param pan: Pan position (-1.0 to 1.0)
        :param tilt: Tilt position (-1.0 to 1.0)
        :param zoom: Zoom position (0.0 to 1.0)
        """
        try:
            request = self.ptz.create_type('AbsoluteMove')
            request.ProfileToken = self.media_profile
            request.Position = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': zoom}
            self.ptz.AbsoluteMove(request)
            logger.info(f"Absolute move: pan={pan}, tilt={tilt}, zoom={zoom}")
        except Exception as e:
            logger.error(f"Failed to execute absolute move: {str(e)}")
            raise

    def get_status(self):
        """Get current PTZ status"""
        try:
            status = self.ptz.GetStatus({'ProfileToken': self.media_profile})
            return {
                'position': status.Position,
                'moving': status.MoveStatus
            }
        except Exception as e:
            logger.error(f"Failed to get PTZ status: {str(e)}")
            raise 