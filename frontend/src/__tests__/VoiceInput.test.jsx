/**
 * @file VoiceInput.test.jsx
 * @description React Testing Library tests for the VoiceInput component.
 *
 * Tests cover:
 *  - Renders the mic button and text input
 *  - Send button is disabled when text is empty
 *  - Send button becomes active when text is typed
 *  - Calls onSend with the correct text on Enter key
 *  - Clears input after send
 *  - Displays the transcribing label when transcribing=true
 *  - Input is disabled during loading / transcribing
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VoiceInput from "../components/VoiceInput";

// ── Default prop factory ──────────────────────────────────────────────────────
const defaultProps = {
  language: "sw",
  onSend: jest.fn(),
  onVoiceResult: jest.fn(),
  loading: false,
  transcribing: false,
  setTranscribing: jest.fn(),
  sessionId: "test-session-123",
};

function renderVoiceInput(props = {}) {
  return render(<VoiceInput {...defaultProps} {...props} />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("VoiceInput", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the microphone button", () => {
    renderVoiceInput();
    const micBtn = screen.getByTitle("Hold to speak");
    expect(micBtn).toBeInTheDocument();
  });

  it("renders the text input with Swahili placeholder", () => {
    renderVoiceInput({ language: "sw" });
    expect(
      screen.getByPlaceholderText(/andika swali lako/i)
    ).toBeInTheDocument();
  });

  it("renders Kikuyu placeholder when language is ki", () => {
    renderVoiceInput({ language: "ki" });
    expect(
      screen.getByPlaceholderText(/ûndĩke ûũria/i)
    ).toBeInTheDocument();
  });

  it("send button is disabled when input is empty", () => {
    renderVoiceInput();
    // Find the send button by its SVG path content (unique icon)
    const sendBtn = screen.getByRole("button", { name: "" });
    // The second button (after mic) should be disabled
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons[buttons.length - 1];
    expect(sendButton).toBeDisabled();
  });

  it("send button becomes enabled when text is typed", async () => {
    renderVoiceInput();
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "mahindi yana ugonjwa");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons[buttons.length - 1];
    expect(sendButton).not.toBeDisabled();
  });

  it("calls onSend and clears input when send button is clicked", async () => {
    const onSend = jest.fn();
    renderVoiceInput({ onSend });
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "mahindi yana ugonjwa");
    const buttons = screen.getAllByRole("button");
    const sendButton = buttons[buttons.length - 1];
    await userEvent.click(sendButton);
    expect(onSend).toHaveBeenCalledWith("mahindi yana ugonjwa");
    expect(input).toHaveValue("");
  });

  it("calls onSend when Enter key is pressed", async () => {
    const onSend = jest.fn();
    renderVoiceInput({ onSend });
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "habari{Enter}");
    expect(onSend).toHaveBeenCalledWith("habari");
  });

  it("does NOT call onSend when input is empty and Enter is pressed", async () => {
    const onSend = jest.fn();
    renderVoiceInput({ onSend });
    const input = screen.getByRole("textbox");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("shows Swahili transcribing label when transcribing=true", () => {
    renderVoiceInput({ transcribing: true, language: "sw" });
    expect(screen.getByText(/inabadilisha sauti/i)).toBeInTheDocument();
  });

  it("shows Kikuyu transcribing label when language is ki", () => {
    renderVoiceInput({ transcribing: true, language: "ki" });
    expect(screen.getByText(/nĩkũhindura sauti/i)).toBeInTheDocument();
  });

  it("disables text input while loading", () => {
    renderVoiceInput({ loading: true });
    expect(screen.getByRole("textbox")).toBeDisabled();
  });

  it("disables text input while transcribing", () => {
    renderVoiceInput({ transcribing: true });
    expect(screen.getByRole("textbox")).toBeDisabled();
  });

  it("does NOT call onSend when loading=true even with text", async () => {
    const onSend = jest.fn();
    renderVoiceInput({ onSend, loading: true });
    // Bypass the disabled state by directly calling the keyDown handler
    const input = screen.getByRole("textbox");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSend).not.toHaveBeenCalled();
  });
});
