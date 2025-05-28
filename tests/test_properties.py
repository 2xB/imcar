# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.abspath(os.path.join(__file__, "..", "..")))

from mca_api.properties import EmptyProperties, PropertyInt, PropertyDict, PropertyBoolean
from mca_api.device import DeviceMCA

def dummy_properties():
    """
    Create array of example 'properties' objecs.
    """
    class SingleIndirectProperty(EmptyProperties):
        indirect = [PropertyInt("Property 1",1,3,2,lambda val,dev: print("Tested: Property 1 -",val))]

    class SingleDirectProperty(EmptyProperties):
        direct = [PropertyInt("Property 1",1,3,2,lambda val,dev: print("Tested: Property 1 -",val))]
    
    class SimplePropertiesSet(EmptyProperties):
        indirect = [PropertyBoolean("Prop indirect 1",False,lambda val,dev: print("Tested: I Property indirect 1 -",val)),
                    PropertyInt("Prop Int 3",2,22,21,lambda val,dev: print("Tested: I Property Int 3 -",val)),
                    PropertyDict("Dictionary",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText",\
                                 lambda val,dev: print("Tested: I Dictionary -",val))]
        direct = [PropertyInt("Prop 1",1,3,2,lambda val,dev: print("Tested: D Property 1 -",val)),
                  PropertyInt("Prop 2",-10,50,2,lambda val,dev: print("Tested: D Property 2 -",val)),
                  PropertyBoolean("Prop direct 1",True,lambda val,dev: print("Tested: D Property direct 1 -",val))]

    class LargePropertiesSet(EmptyProperties):
        indirect = [PropertyBoolean("Prop indirect 1",False,lambda val,dev: print("Tested: I Property indirect 1 -",val)),
                    PropertyInt("Prop Int 3",2,22,21,lambda val,dev: print("Tested: I Property Int 3 -",val)),
                    PropertyDict("Dictionary",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText",\
                                 lambda val,dev: print("Tested: I Dictionary -",val)),
                    PropertyInt("Prop Int 2",2,22,21),
                    PropertyDict("Dictionary2",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText"),
                    PropertyInt("Prop Int 3",2,22,21),
                    PropertyDict("Dictionary3",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText"),
                    PropertyInt("Prop Int 4",2,22,21),
                    PropertyDict("Dictionary4",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText"),
                  PropertyInt("Prop 1",-10,50,2),
                  PropertyBoolean("Prop direct 1",True),
                  PropertyInt("Prop 2",-10,50,2),
                  PropertyBoolean("Prop direct 1",True),
                  PropertyInt("Prop 3",-10,50,2),
                  PropertyBoolean("Prop direct 1",True),
                    PropertyDict("Dictionary",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText"),
                    PropertyDict("Dictionary",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText"),
                    PropertyDict("Dictionary",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText"),
                  PropertyInt("Prop 4",-10,50,2),
                  PropertyBoolean("Prop direct last",True)]
        direct = [PropertyInt("Prop 1",1,3,2,lambda val,dev: print("Tested: D Property 1 -",val)),
                  PropertyInt("Prop 2",-10,50,2,lambda val,dev: print("Tested: D Property 2 -",val)),
                  PropertyBoolean("Prop direct 1",True),
                  PropertyInt("Prop 3",-10,50,2),
                  PropertyBoolean("Prop direct 2",True),
                  PropertyInt("Prop 4",-9,60,-9),
                  PropertyBoolean("Prop direct 3",True),
                  PropertyInt("Prop 5",-10,5000,5000),
                  PropertyBoolean("Prop direct 4",True),
                  PropertyInt("Prop 6",-10,50,2),
                  PropertyBoolean("Prop direct 5",True),
                  PropertyInt("Prop 7",-10,50,2),
                  PropertyBoolean("Prop direct 6",True),
                  PropertyInt("Prop 8",-10,50,2),
                  PropertyBoolean("Prop direct 7",True),
                  PropertyInt("Prop 9",-10,50,2),
                  PropertyBoolean("Prop direct 8",True),
                  PropertyInt("Prop 10",-10,50,2),
                  PropertyBoolean("Prop direct 9",True),
                  PropertyInt("Prop 11",-10,50,2),
                  PropertyBoolean("Prop direct 10",True),
                  PropertyInt("Prop 12",-10,50,2),
                  PropertyBoolean("Prop direct 11",True),
                  PropertyInt("Prop 12",-10,50,2),
                  PropertyBoolean("Prop direct 12",True),
                  PropertyInt("Prop 13",-10,50,2),
                  PropertyBoolean("Prop direct 13",True),
                    PropertyDict("Dictionary",{"Text1":1,"DefaultText":3,"Third text":-1},"DefaultText"),
                  PropertyInt("Prop 15",-10,50,2),
                  PropertyBoolean("Prop direct 14",True)]

    return [EmptyProperties(DeviceMCA()), 
            SingleIndirectProperty(DeviceMCA()), 
            SingleDirectProperty(DeviceMCA()),
            SimplePropertiesSet(DeviceMCA()),
            LargePropertiesSet(DeviceMCA())]

if __name__ == "__main__":
    pass
