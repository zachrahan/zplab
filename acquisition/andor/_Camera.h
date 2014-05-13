// Copyright 2014 WUSTL ZPLAB

#pragma once
#include "_common.h"

// Making this copyable would require keeping a reference count to m_dh such that the destructor of the last instance of
// a copied _Camera object would close m_dh.  Otherwise, the first instance destroyed would close m_dh, leaving any
// extant copies with an invalid handle.
class _Camera
  : boost::noncopyable
{
public:
    enum class Feature
    {
        _Begin = 0,
        AccumulateCount = _Begin,
        AcquisitionStart,
        AcquisitionStop,
        AOIBinning,
        AOIHBin,
        AOIHeight,
        AOILeft,
        AOIStride,
        AOITop,
        AOIVBin,
        AOIWidth,
        AuxiliaryOutSource,
        BaselineLevel,
        BitDepth,
        BufferOverflowEvent,
        BytesPerPixel,
        CameraAcquiring,
        CameraDump,
        CameraModel,
        CameraName,
        ControllerID,
        CycleMode,
        DeviceCount,
        DeviceVideoIndex,
        ElectronicShutteringMode,
        EventEnable,
        EventsMissedEvent,
        EventSelector,
        ExposureTime,
        ExposureEndEvent,
        ExposureStartEvent,
        FanSpeed,
        FirmwareVersion,
        FrameCount,
        FrameRate,
        FullAOIControl,
        ImageSizeBytes,
        InterfaceType,
        IOInvert,
        IOSelector,
        LUTIndex,
        LUTValue,
        MaxInterfaceTransferRate,
        MetadataEnable,
        MetadataFrame,
        MetadataTimestamp,
        Overlap,
        PixelCorrection,
        PixelEncoding,
        PixelHeight,
        PixelReadoutRate,
        PixelWidth,
        PreAmpGain,
        PreAmpGainChannel,
        PreAmpGainControl,
        PreAmpGainSelector,
        ReadoutTime,
        RollingShutterGlobalClear,
        RowNExposureEndEvent,
        RowNExposureStartEvent,
        SensorCooling,
        SensorHeight,
        SensorTemperature,
        SensorWidth,
        SerialNumber,
        SimplePreAmpGainControl,
        SoftwareTrigger,
        SoftwareVersion,
        SpuriousNoiseFilter,
        SynchronousTriggering,
        TargetSensorTemperature,
        TemperatureControl,
        TemperatureStatus,
        TimestampClock,
        TimestampClockFrequency,
        TimestampClockReset,
        TriggerMode,
        VerticallyCenterAOI,
        _End
    };

    enum class SimplePreAmp : int
    {
        _Begin = 0,
        HighCapacity_12bit = _Begin,
        LowNoise_12bit,
        LowNoiseHighCapacity_16bit,
        _End
    };

    enum class Shutter : int
    {
        _Begin = 0,
        Rolling = _Begin,
        Global,
        _End
    };

    enum class TriggerMode : int
    {
        _Begin = 0,
        Internal= _Begin,
        ExternalLevelTransition,
        ExternalStart,
        ExternalExposure,
        Software,
        Advanced,
        External,
        _End
    };

    class _CallbackRegistrationToken
      : boost::noncopyable
    {
    public:
        _CallbackRegistrationToken() = delete;
        ~_CallbackRegistrationToken();
        bool operator == (const _CallbackRegistrationToken& rhs) const;
        bool operator != (const _CallbackRegistrationToken& rhs) const;
    protected:
        _CallbackRegistrationToken(_Camera& camera_, const Feature& feature_, const std::function<bool(Feature)>& callback_);
        _Camera& m_camera;
        Feature m_feature;
        std::function<bool(Feature)> m_callback;
        bool m_precalled;
        friend _Camera;
    };

    static std::shared_ptr<std::vector<std::string>> getDeviceNames();
    static const wchar_t* lookupFeatureName(const Feature& feature);

    explicit _Camera(const AT_64& deviceIndex);
    virtual ~_Camera();

    /* Functions that map directly to Andor API calls */

    std::shared_ptr<_CallbackRegistrationToken> AT_RegisterFeatureCallback(const Feature& feature, const std::function<bool(Feature)>& callback);
    std::shared_ptr<_CallbackRegistrationToken> AT_RegisterFeatureCallbackPyWrapper(const Feature& feature, py::object pyCallback);
    void AT_UnregisterFeatureCallback(const std::shared_ptr<_CallbackRegistrationToken>& crt);

    bool AT_IsImplemented(const Feature& feature);
    bool AT_IsReadable(const Feature& feature);
    bool AT_IsWritable(const Feature& feature);
    bool AT_IsReadOnly(const Feature& feature);

    void AT_SetInt(const Feature& feature, const AT_64& value);
    AT_64 AT_GetInt(const Feature& feature);
    AT_64 AT_GetIntMax(const Feature& feature);
    AT_64 AT_GetIntMin(const Feature& feature);

    void AT_SetFloat(const Feature& feature, const double& value);
    double AT_GetFloat(const Feature& feature);
    double AT_GetFloatMax(const Feature& feature);
    double AT_GetFloatMin(const Feature& feature);

    void AT_SetBool(const Feature& feature, const bool& value);
    bool AT_GetBool(const Feature& feature);

    void AT_SetEnumIndex(const Feature& feature, const int& value);
    void AT_SetEnumString(const Feature& feature, const std::string& value);
    int AT_GetEnumIndex(const Feature& feature);
    int AT_GetEnumCount(const Feature& feature);
    bool AT_IsEnumIndexAvailable(const Feature& feature, const int& index);
    bool AT_IsEnumIndexImplemented(const Feature& feature, const int& index);
    std::string AT_GetEnumStringByIndex(const Feature& feature, const int& index);

    void AT_Command(const Feature& feature);

    void AT_SetString(const Feature& feature, const std::string& value);
    std::string AT_GetString(const Feature& feature);
    int AT_GetStringMaxLength(const Feature& feature);

    void AT_QueueBuffer(np::ndarray buff);
    std::uintptr_t AT_WaitBuffer(const unsigned int& timeout);
    void AT_Flush();

    /* Convenience functions that provide a more abstracted interface to the Andor API */

    SimplePreAmp simplePreAmp() const;
    void simplePreAmp(const SimplePreAmp& simplePreAmp_);

    Shutter shutter() const;
    void shutter(const Shutter& shutter_);

    TriggerMode triggerMode() const;
    void triggerMode(const TriggerMode& triggerMode_);

protected:
    static const wchar_t *sm_featureNames[];
    static const wchar_t *sm_simplePreAmpNames[];
    static const wchar_t *sm_shutterNames[];
    static const wchar_t *sm_triggerModeNames[];

    // Device handle
    AT_H m_dh;

    // Callback Registration TokenS
    typedef std::set<std::shared_ptr<_CallbackRegistrationToken>> Crts;
    Crts m_crts;

    static int AT_EXP_CONV atCallbackWrapper(AT_H dh, const AT_WC* calledFeatureName, void* crtvp);
};
