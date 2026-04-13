#pragma once

#include <JuceHeader.h>
#include "PapGeneratedParameters.h"
#include "PapDSPBlocks.h"
#include "PapSignalGraph.h"
#include "PapCliControl.h"

class ${plugin_name}AudioProcessor : public juce::AudioProcessor
{
public:
    ${plugin_name}AudioProcessor();
    ~${plugin_name}AudioProcessor() override = default;

    void prepareToPlay(double sampleRate, int samplesPerBlock) override;
    void releaseResources() override;
    bool isBusesLayoutSupported(const BusesLayout& layouts) const override;
    void processBlock(juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return "${plugin_name}"; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram(int) override {}
    const juce::String getProgramName(int) override { return {}; }
    void changeProgramName(int, const juce::String&) override {}

    void getStateInformation(juce::MemoryBlock& destData) override;
    void setStateInformation(const void* data, int sizeInBytes) override;

    const char* getPapSignalFlow() const noexcept { return pap::getPapSignalGraph(); }
    juce::AudioProcessorValueTreeState& getValueTreeState() noexcept { return parameters; }

private:
    juce::AudioProcessorValueTreeState parameters;
    juce::LinearSmoothedValue<float> outputGain;
    pap::CliControlBridge cliControl;
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(${plugin_name}AudioProcessor)
};
