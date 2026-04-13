#pragma once

#include <JuceHeader.h>
#include <array>
#include <memory>
#include <vector>
#include "PluginProcessor.h"
#include "PapUiRuntime.h"

class ${plugin_name}AudioProcessorEditor : public juce::AudioProcessorEditor
{
public:
    explicit ${plugin_name}AudioProcessorEditor(${plugin_name}AudioProcessor&);
    ~${plugin_name}AudioProcessorEditor() override = default;

    void paint(juce::Graphics&) override;
    void resized() override;

private:
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;

    struct ParamStrip
    {
        juce::Slider slider;
        juce::Label label;
        std::unique_ptr<SliderAttachment> attachment;
    };

    ${plugin_name}AudioProcessor& audioProcessor;
    juce::Label title;
    juce::Label subtitle;
    juce::Label runtimeBadge;
    juce::Label bridgeBadge;
    juce::Label flowLabel;
    juce::Label checkpointLabel;
    std::vector<std::unique_ptr<ParamStrip>> strips;

    void buildPrimaryControls();
    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR(${plugin_name}AudioProcessorEditor)
};
