#include "PluginProcessor.h"
#include "PluginEditor.h"

void PapSimpleVoice::startNote(int midiNoteNumber, float velocity, juce::SynthesiserSound*, int)
{
    level = velocity;
    osc.setFrequency(juce::MidiMessage::getMidiNoteInHertz(midiNoteNumber));
    adsr.noteOn();
}

void PapSimpleVoice::stopNote(float, bool allowTailOff)
{
    adsr.noteOff();
    if (! allowTailOff || ! adsr.isActive())
        clearCurrentNote();
}

void PapSimpleVoice::renderNextBlock(juce::AudioBuffer<float>& buffer, int startSample, int numSamples)
{
    auto* left = buffer.getWritePointer(0, startSample);
    auto* right = buffer.getNumChannels() > 1 ? buffer.getWritePointer(1, startSample) : nullptr;
    for (int i = 0; i < numSamples; ++i)
    {
        const auto env = adsr.getNextSample();
        const auto sample = osc.processSample(0.0f) * env * level * 0.2f;
        left[i] += sample;
        if (right != nullptr)
            right[i] += sample;
    }
    if (! adsr.isActive())
        clearCurrentNote();
}

${plugin_name}AudioProcessor::${plugin_name}AudioProcessor()
    : juce::AudioProcessor(BusesProperties().withOutput("Output", juce::AudioChannelSet::stereo(), true)),
      parameters(*this, nullptr, "PARAMETERS", pap::createParameterLayout())
{
    for (int i = 0; i < 8; ++i)
        synth.addVoice(new PapSimpleVoice());
    synth.addSound(new PapSimpleSound());
}

void ${plugin_name}AudioProcessor::prepareToPlay(double sampleRate, int samplesPerBlock)
{
    juce::dsp::ProcessSpec spec{sampleRate, static_cast<juce::uint32>(samplesPerBlock), 2};
    for (int i = 0; i < synth.getNumVoices(); ++i)
        if (auto* voice = dynamic_cast<PapSimpleVoice*>(synth.getVoice(i)))
            voice->osc.prepare(spec);
    synth.setCurrentPlaybackSampleRate(sampleRate);
}

bool ${plugin_name}AudioProcessor::isBusesLayoutSupported(const BusesLayout& layouts) const
{
    return layouts.getMainOutputChannelSet() == juce::AudioChannelSet::stereo();
}

void ${plugin_name}AudioProcessor::processBlock(juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)
{
    juce::ScopedNoDenormals noDenormals;
    cliControl.pollAndApply(parameters, &midi);
    buffer.clear();
    synth.renderNextBlock(buffer, midi, 0, buffer.getNumSamples());
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
