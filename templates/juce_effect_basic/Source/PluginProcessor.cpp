#include "PluginProcessor.h"
#include "PluginEditor.h"

${plugin_name}AudioProcessor::${plugin_name}AudioProcessor()
    : juce::AudioProcessor(BusesProperties().withInput("Input", juce::AudioChannelSet::stereo(), true)
                                           .withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      parameters(*this, nullptr, "PARAMETERS", pap::createParameterLayout())
{
}

void ${plugin_name}AudioProcessor::prepareToPlay(double sampleRate, int)
{
    outputGain.reset(sampleRate, 0.05);
}

void ${plugin_name}AudioProcessor::releaseResources() {}

bool ${plugin_name}AudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    return layouts.getMainInputChannelSet() == juce::AudioChannelSet::stereo()
        && layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
}

void ${plugin_name}AudioProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;
    cliControl.pollAndApply(parameters, nullptr);
    const auto outputDb = *parameters.getRawParameterValue("output");
    outputGain.setTargetValue(juce::Decibels::decibelsToGain(outputDb));

    for (int channel = 0; channel < buffer.getNumChannels(); ++channel)
    {
        auto* data = buffer.getWritePointer(channel);
        for (int i = 0; i < buffer.getNumSamples(); ++i)
            data[i] *= outputGain.getNextValue();
    }
}

juce::AudioProcessorEditor* ${plugin_name}AudioProcessor::createEditor()
{
    return new ${plugin_name}AudioProcessorEditor(*this);
}

void ${plugin_name}AudioProcessor::getStateInformation(juce::MemoryBlock& destData)
{
    if (auto xml = parameters.copyState().createXml())
        copyXmlToBinary(*xml, destData);
}

void ${plugin_name}AudioProcessor::setStateInformation(const void* data, int sizeInBytes)
{
    if (auto xmlState = getXmlFromBinary(data, sizeInBytes))
        parameters.replaceState(juce::ValueTree::fromXml(*xmlState));
}
