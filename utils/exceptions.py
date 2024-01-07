class TamperingException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
        
    def __str__(self):
        return self.message
    
class FaceEncodingException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
        
    def __str__(self):
        return self.message
    
class PathExtractionException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)
        
    def __str__(self):
        return self.message