// Copyright 2014 WUSTL ZPLAB
#include <csignal>
#include "_common.h"
#include "_AndorException.h"
#include "_Api.h"
#include "_Camera.h"

using namespace boost::python;

static void andorExceptionBaseTranslator(const std::shared_ptr<object>& andorExceptionType, const _AndorExceptionBase& _andorExceptionBase)
{
//  std::cerr << "static void andorExceptionBaseTranslator(const std::shared_ptr<object>& andorExceptionType, const _AndorExceptionBase& _andorExceptionBase)\n";
    // The following line is roughly equivalent to the python "andorException = 
    // AndorException(_andorExceptionBase.description())"
    object andorException{ (*andorExceptionType)(_andorExceptionBase.description().c_str()) };
    PyErr_SetObject(andorExceptionType->ptr(), andorException.ptr() );
}

static void andorExceptionTranslator(const std::shared_ptr<object>& andorExceptionType, const _AndorException& _andorException)
{
//  std::cerr << "static void andorExceptionTranslator(const std::shared_ptr<object>& andorExceptionType, const _AndorException& _andorException)\n";
    // The following line is roughly equivalent to the python "andorException = 
    // AndorException(_andorException.description(), _andorException.errorCode(), _andorException.errorName())"
    object andorException{ (*andorExceptionType)(_andorException.description().c_str(), _andorException.errorCode(), _andorException.errorName().c_str()) };
    PyErr_SetObject(andorExceptionType->ptr(), andorException.ptr() );
}

// static std::string test()
// {
//  return std::string("Héllø ∑ô¡™£¢d!");
// }

// static unsigned long testndarray(np::ndarray a)
// {
//  std::cout << py::extract<const char*>(py::str(a)) << std::endl;
//  const Py_intptr_t* strides = a.get_strides();
//  *reinterpret_cast<float*>(a.get_data() + 2 * strides[0] + 1 * strides[1]) += 5.1f;
//  unsigned long m(std::numeric_limits<unsigned long>::max());
//  std::cout << m << std::endl;
//  return m;
// }

// Note that this block is executed by the Python interpreter when this module is loaded
BOOST_PYTHON_MODULE(_andor)
{
    try
    {
        // This is not a stand-alone C++ application that embeds a Python interpreter (if it were, we would call
        // Py_Initialize here).  This is a C++ module that must be loaded by an existing interpreter instance.
        // Therefore, if the interpreter has not been initialized, something is amiss.
        if(Py_IsInitialized() == 0)
        {
            std::cerr << "_andor Python module attempted to load while Python interpreter is not initialized (Py_IsInitialized() == 0).\n";
            Py_Exit(-1);
        }
        // If the Python interpreter remains single threaded and no threads are made by this module that interpret
        // Python code, then no GIL-related code is necessary and could be if-ed out for the special single-threaded
        // case.  However, that would increase the complexity of the C++ code.  Instead, we ensure that Python threading
        // is active, accepting the small speed hit incurred by manipulating the GIL even when executing in a single
        // threaded context that does not benefit from our doing so.  If Python threading has been initialized by the
        // time this module is loaded (ie, thread.Thread(..).start() has been called in Python), PyEval_InitThreads is a
        // no-op.
        PyEval_InitThreads();
        np::initialize();
        _Camera::staticInit();

        // Import our Python exception module
        object andorExceptionPackage{import("acquisition.andor.andor_exception")};
        // Get our exception class type from the module.  Note that the lambda below should be able to capture a
        // boost::python::object directly such that the object is retained while an instance of the lambda exists.  For
        // whatever reason, the captured boost::python::object does not retain its python object, and so the shared_ptr
        // mechanism is instead used to manage the boost::python::object's lifetime and therefore the lifetime of the
        // python object itself.
        std::shared_ptr<object> andorExceptionType{ new object(andorExceptionPackage.attr("AndorException")) };
        // Register C++ to python exception translators
        register_exception_translator<_AndorExceptionBase>( [=](const _AndorExceptionBase& _andorExceptionBase){andorExceptionBaseTranslator(andorExceptionType, _andorExceptionBase);} );
        register_exception_translator<_AndorException>( [=](const _AndorException& _andorException){andorExceptionTranslator(andorExceptionType, _andorException);} );

        // Initialize Andor SDK3 API library
        _Api::instantiate();

//      def("test", test);
//      def("testndarray", testndarray);

        class_< std::vector<std::string>, std::shared_ptr<std::vector<std::string>> >("StringVector")
            .def( vector_indexing_suite<std::vector<std::string> >());

        scope cameraScope =
        class_<_Camera, boost::noncopyable>("_Camera", init<AT_64>())
            .def("getDeviceNames", &_Camera::getDeviceNames)
            .staticmethod("getDeviceNames")
            .def("AT_RegisterFeatureCallback", &_Camera::AT_RegisterFeatureCallbackPyWrapper)
            .def("AT_UnregisterFeatureCallback", &_Camera::AT_UnregisterFeatureCallback)
            .def("AT_IsImplemented", &_Camera::AT_IsImplemented)
            .def("AT_IsReadable", &_Camera::AT_IsReadable)
            .def("AT_IsWritable", &_Camera::AT_IsWritable)
            .def("AT_IsReadOnly", &_Camera::AT_IsReadOnly)
            .def("AT_SetInt", &_Camera::AT_SetInt)
            .def("AT_GetInt", &_Camera::AT_GetInt)
            .def("AT_GetIntMax", &_Camera::AT_GetIntMax)
            .def("AT_GetIntMin", &_Camera::AT_GetIntMin)
            .def("AT_SetFloat", &_Camera::AT_SetFloat)
            .def("AT_GetFloat", &_Camera::AT_GetFloat)
            .def("AT_GetFloatMax", &_Camera::AT_GetFloatMax)
            .def("AT_GetFloatMin", &_Camera::AT_GetFloatMin)
            .def("AT_SetBool", &_Camera::AT_SetBool)
            .def("AT_GetBool", &_Camera::AT_GetBool)
            .def("AT_SetEnumIndex", &_Camera::AT_SetEnumIndex)
            .def("AT_SetEnumString", &_Camera::AT_SetEnumString)
            .def("AT_GetEnumIndex", &_Camera::AT_GetEnumIndex)
            .def("AT_GetEnumCount", &_Camera::AT_GetEnumCount)
            .def("AT_IsEnumIndexAvailable", &_Camera::AT_IsEnumIndexAvailable)
            .def("AT_IsEnumIndexImplemented", &_Camera::AT_IsEnumIndexImplemented)
            .def("AT_GetEnumStringByIndex", &_Camera::AT_GetEnumStringByIndex)
            .def("AT_Command", &_Camera::AT_Command)
            .def("AT_SetString", &_Camera::AT_SetString)
            .def("AT_GetString", &_Camera::AT_GetString)
            .def("AT_GetStringMaxLength", &_Camera::AT_GetStringMaxLength)
            .def("AT_QueueBuffer", &_Camera::AT_QueueBuffer)
            .def("AT_WaitBuffer", &_Camera::AT_WaitBuffer)
            .def("AT_Flush", &_Camera::AT_Flush)
            .add_property("temperatureStatus", &_Camera::temperatureStatus)
            .add_property("pixelEncoding", &_Camera::pixelEncoding)
            // The following properties have getters and setters that share overloaded function names and must therefore
            // be addressed with fully qualified function pointer types.
            .add_property("simplePreAmp",
                          (_Camera::SimplePreAmp (_Camera::*)() const) &_Camera::simplePreAmp,
                          (void (_Camera::*)(const _Camera::SimplePreAmp&)) &_Camera::simplePreAmp)
            .add_property("shutter",
                          (_Camera::Shutter (_Camera::*)() const) &_Camera::shutter,
                          (void (_Camera::*)(const _Camera::Shutter&)) &_Camera::shutter)
            .add_property("triggerMode",
                          (_Camera::TriggerMode (_Camera::*)() const) &_Camera::triggerMode,
                          (void (_Camera::*)(const _Camera::TriggerMode&)) &_Camera::triggerMode)
            .add_property("binning",
                          (_Camera::Binning (_Camera::*)() const) &_Camera::binning,
                          (void (_Camera::*)(const _Camera::Binning&)) &_Camera::binning)
            .add_property("auxiliaryOutSource",
                          (_Camera::AuxiliaryOutSource (_Camera::*)() const) &_Camera::auxiliaryOutSource,
                          (void (_Camera::*)(const _Camera::AuxiliaryOutSource&)) &_Camera::auxiliaryOutSource)
            .add_property("cycleMode",
                          (_Camera::CycleMode (_Camera::*)() const) &_Camera::cycleMode,
                          (void (_Camera::*)(const _Camera::CycleMode&)) &_Camera::cycleMode)
            .add_property("fanSpeed",
                          (_Camera::FanSpeed (_Camera::*)() const) &_Camera::fanSpeed,
                          (void (_Camera::*)(const _Camera::FanSpeed&)) &_Camera::fanSpeed)
            .add_property("ioSelector",
                          (_Camera::IOSelector (_Camera::*)() const) &_Camera::ioSelector,
                          (void (_Camera::*)(const _Camera::IOSelector&)) &_Camera::ioSelector);

        class_<_Camera::_CallbackRegistrationToken, std::shared_ptr<_Camera::_CallbackRegistrationToken>, boost::noncopyable>("_CallbackRegistrationToken", no_init);

        enum_<_Camera::Feature>("Feature")
            .value("AccumulateCount", _Camera::Feature::AccumulateCount)
            .value("AcquisitionStart", _Camera::Feature::AcquisitionStart)
            .value("AcquisitionStop", _Camera::Feature::AcquisitionStop)
            .value("AOIBinning", _Camera::Feature::AOIBinning)
            .value("AOIHBin", _Camera::Feature::AOIHBin)
            .value("AOIHeight", _Camera::Feature::AOIHeight)
            .value("AOILeft", _Camera::Feature::AOILeft)
            .value("AOIStride", _Camera::Feature::AOIStride)
            .value("AOITop", _Camera::Feature::AOITop)
            .value("AOIVBin", _Camera::Feature::AOIVBin)
            .value("AOIWidth", _Camera::Feature::AOIWidth)
            .value("AuxiliaryOutSource", _Camera::Feature::AuxiliaryOutSource)
            .value("BaselineLevel", _Camera::Feature::BaselineLevel)
            .value("BitDepth", _Camera::Feature::BitDepth)
            .value("BufferOverflowEvent", _Camera::Feature::BufferOverflowEvent)
            .value("BytesPerPixel", _Camera::Feature::BytesPerPixel)
            .value("CameraAcquiring", _Camera::Feature::CameraAcquiring)
            .value("CameraDump", _Camera::Feature::CameraDump)
            .value("CameraModel", _Camera::Feature::CameraModel)
            .value("CameraName", _Camera::Feature::CameraName)
            .value("ControllerID", _Camera::Feature::ControllerID)
            .value("CycleMode", _Camera::Feature::CycleMode)
            .value("DeviceCount", _Camera::Feature::DeviceCount)
            .value("DeviceVideoIndex", _Camera::Feature::DeviceVideoIndex)
            .value("ElectronicShutteringMode", _Camera::Feature::ElectronicShutteringMode)
            .value("EventEnable", _Camera::Feature::EventEnable)
            .value("EventsMissedEvent", _Camera::Feature::EventsMissedEvent)
            .value("EventSelector", _Camera::Feature::EventSelector)
            .value("ExposureTime", _Camera::Feature::ExposureTime)
            .value("ExposureEndEvent", _Camera::Feature::ExposureEndEvent)
            .value("ExposureStartEvent", _Camera::Feature::ExposureStartEvent)
            .value("FanSpeed", _Camera::Feature::FanSpeed)
            .value("FirmwareVersion", _Camera::Feature::FirmwareVersion)
            .value("FrameCount", _Camera::Feature::FrameCount)
            .value("FrameRate", _Camera::Feature::FrameRate)
            .value("FullAOIControl", _Camera::Feature::FullAOIControl)
            .value("ImageSizeBytes", _Camera::Feature::ImageSizeBytes)
            .value("InterfaceType", _Camera::Feature::InterfaceType)
            .value("IOInvert", _Camera::Feature::IOInvert)
            .value("IOSelector", _Camera::Feature::IOSelector)
            .value("LUTIndex", _Camera::Feature::LUTIndex)
            .value("LUTValue", _Camera::Feature::LUTValue)
            .value("MaxInterfaceTransferRate", _Camera::Feature::MaxInterfaceTransferRate)
            .value("MetadataEnable", _Camera::Feature::MetadataEnable)
            .value("MetadataFrame", _Camera::Feature::MetadataFrame)
            .value("MetadataTimestamp", _Camera::Feature::MetadataTimestamp)
            .value("Overlap", _Camera::Feature::Overlap)
            .value("PixelCorrection", _Camera::Feature::PixelCorrection)
            .value("PixelEncoding", _Camera::Feature::PixelEncoding)
            .value("PixelHeight", _Camera::Feature::PixelHeight)
            .value("PixelReadoutRate", _Camera::Feature::PixelReadoutRate)
            .value("PixelWidth", _Camera::Feature::PixelWidth)
            .value("PreAmpGain", _Camera::Feature::PreAmpGain)
            .value("PreAmpGainChannel", _Camera::Feature::PreAmpGainChannel)
            .value("PreAmpGainControl", _Camera::Feature::PreAmpGainControl)
            .value("PreAmpGainSelector", _Camera::Feature::PreAmpGainSelector)
            .value("ReadoutTime", _Camera::Feature::ReadoutTime)
            .value("RollingShutterGlobalClear", _Camera::Feature::RollingShutterGlobalClear)
            .value("RowNExposureEndEvent", _Camera::Feature::RowNExposureEndEvent)
            .value("RowNExposureStartEvent", _Camera::Feature::RowNExposureStartEvent)
            .value("SensorCooling", _Camera::Feature::SensorCooling)
            .value("SensorHeight", _Camera::Feature::SensorHeight)
            .value("SensorTemperature", _Camera::Feature::SensorTemperature)
            .value("SensorWidth", _Camera::Feature::SensorWidth)
            .value("SerialNumber", _Camera::Feature::SerialNumber)
            .value("SimplePreAmpGainControl", _Camera::Feature::SimplePreAmpGainControl)
            .value("SoftwareTrigger", _Camera::Feature::SoftwareTrigger)
            .value("SoftwareVersion", _Camera::Feature::SoftwareVersion)
            .value("SpuriousNoiseFilter", _Camera::Feature::SpuriousNoiseFilter)
            .value("SynchronousTriggering", _Camera::Feature::SynchronousTriggering)
            .value("TargetSensorTemperature", _Camera::Feature::TargetSensorTemperature)
            .value("TemperatureControl", _Camera::Feature::TemperatureControl)
            .value("TemperatureStatus", _Camera::Feature::TemperatureStatus)
            .value("TimestampClock", _Camera::Feature::TimestampClock)
            .value("TimestampClockFrequency", _Camera::Feature::TimestampClockFrequency)
            .value("TimestampClockReset", _Camera::Feature::TimestampClockReset)
            .value("TriggerMode", _Camera::Feature::TriggerMode)
            .value("VerticallyCenterAOI", _Camera::Feature::VerticallyCenterAOI);

        enum_<_Camera::SimplePreAmp>("SimplePreAmp")
            .value("HighCapacity_12bit", _Camera::SimplePreAmp::HighCapacity_12bit)
            .value("LowNoise_12bit", _Camera::SimplePreAmp::LowNoise_12bit)
            .value("LowNoiseHighCapacity_16bit", _Camera::SimplePreAmp::LowNoiseHighCapacity_16bit)
            .export_values();

        enum_<_Camera::Shutter>("Shutter")
            .value("Rolling", _Camera::Shutter::Rolling)
            .value("Global", _Camera::Shutter::Global)
            .export_values();

        enum_<_Camera::TriggerMode>("TriggerMode")
            .value("Internal", _Camera::TriggerMode::Internal)
            .value("ExternalLevelTransition", _Camera::TriggerMode::ExternalLevelTransition)
            .value("ExternalStart", _Camera::TriggerMode::ExternalStart)
            .value("ExternalExposure", _Camera::TriggerMode::ExternalExposure)
            .value("Software", _Camera::TriggerMode::Software)
            .value("Advanced", _Camera::TriggerMode::Advanced)
            .value("External", _Camera::TriggerMode::External)
            .export_values();

        enum_<_Camera::TemperatureStatus>("TemperatureStatus")
            .value("CoolerOff", _Camera::TemperatureStatus::CoolerOff)
            .value("Stabilized", _Camera::TemperatureStatus::Stabilized)
            .value("Cooling", _Camera::TemperatureStatus::Cooling)
            .value("Drift", _Camera::TemperatureStatus::Drift)
            .value("NotStabilized", _Camera::TemperatureStatus::NotStabilized)
            .value("Fault", _Camera::TemperatureStatus::Fault)
            .export_values();

        enum_<_Camera::Binning>("Binning")
            .value("Bin_1x1", _Camera::Binning::Bin_1x1)
            .value("Bin_2x2", _Camera::Binning::Bin_2x2)
            .value("Bin_3x3", _Camera::Binning::Bin_3x3)
            .value("Bin_4x4", _Camera::Binning::Bin_4x4)
            .value("Bin_8x8", _Camera::Binning::Bin_8x8)
            .export_values();

        enum_<_Camera::AuxiliaryOutSource>("AuxiliaryOutSource")
            .value("FireRow1", _Camera::AuxiliaryOutSource::FireRow1)
            .value("FireRowN", _Camera::AuxiliaryOutSource::FireRowN)
            .value("FireAll", _Camera::AuxiliaryOutSource::FireAll)
            .value("FireAny", _Camera::AuxiliaryOutSource::FireAny)
            .export_values();

        enum_<_Camera::CycleMode>("CycleMode")
            .value("Fixed", _Camera::CycleMode::Fixed)
            .value("Continuous", _Camera::CycleMode::Continuous)
            .export_values();

        enum_<_Camera::FanSpeed>("FanSpeed")
            .value("Off", _Camera::FanSpeed::Off)
            .value("On", _Camera::FanSpeed::On)
            .export_values();

        enum_<_Camera::PixelEncoding>("PixelEncoding")
            .value("Mono12", _Camera::PixelEncoding::Mono12)
            .value("Mono12Packed", _Camera::PixelEncoding::Mono12Packed)
            .value("Mono16", _Camera::PixelEncoding::Mono16)
            .value("RGB8Packed", _Camera::PixelEncoding::RGB8Packed)
            .value("Mono12Coded", _Camera::PixelEncoding::Mono12Coded)
            .value("Mono12CodedPacked", _Camera::PixelEncoding::Mono12CodedPacked)
            .value("Mono22Parallel", _Camera::PixelEncoding::Mono22Parallel)
            .value("Mono22PackedParallel", _Camera::PixelEncoding::Mono22PackedParallel)
            .value("Mono8", _Camera::PixelEncoding::Mono8)
            .value("Mono32", _Camera::PixelEncoding::Mono32)
            .export_values();

        enum_<_Camera::IOSelector>("IOSelector")
            .value("Fire1", _Camera::IOSelector::Fire1)
            .value("FireN", _Camera::IOSelector::FireN)
            .value("AuxOut1", _Camera::IOSelector::AuxOut1)
            .value("Arm", _Camera::IOSelector::Arm)
            .value("AuxOut2", _Camera::IOSelector::AuxOut2)
            .value("SpareInput", _Camera::IOSelector::SpareInput)
            .value("ExternalTrigger", _Camera::IOSelector::ExternalTrigger)
            .value("FireNand1", _Camera::IOSelector::FireNand1)
            .export_values();
    }
    catch(error_already_set const&)
    {
        std::cerr << "Error during initialization of acquisition.andor._andor C++ module:\n";
        PyErr_Print();
        Py_Exit(-1);
    }
}
