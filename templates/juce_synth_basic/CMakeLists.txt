cmake_minimum_required(VERSION 3.22)
project(${plugin_name} VERSION 0.1.0)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(DEFINED JUCE_DIR)
  add_subdirectory(${JUCE_DIR} JUCE)
elseif(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/third_party/JUCE/CMakeLists.txt)
  add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/third_party/JUCE JUCE)
else()
  message(FATAL_ERROR "JUCE_DIR not provided and third_party/JUCE missing.")
endif()

juce_add_plugin(${plugin_name}
    COMPANY_NAME "${vendor_name}"
    IS_SYNTH TRUE
    NEEDS_MIDI_INPUT TRUE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    COPY_PLUGIN_AFTER_BUILD FALSE
    PLUGIN_MANUFACTURER_CODE TzWe
    PLUGIN_CODE PAPS
    FORMATS VST3 Standalone
    PRODUCT_NAME "${plugin_name}")

target_sources(${plugin_name}
    PRIVATE
      Source/PluginProcessor.cpp
      Source/PluginEditor.cpp
      Source/PapGeneratedParameters.cpp
      Source/PapProcessPlan.cpp
      Source/PapCliControl.cpp)

target_compile_definitions(${plugin_name}
    PUBLIC JUCE_WEB_BROWSER=0 JUCE_USE_CURL=0)

target_link_libraries(${plugin_name}
    PRIVATE juce::juce_audio_utils juce::juce_dsp
    PUBLIC juce::juce_recommended_config_flags juce::juce_recommended_lto_flags juce::juce_recommended_warning_flags)
