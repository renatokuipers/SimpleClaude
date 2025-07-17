/**
 * ULTRA-SIMPLE Claude wrapper - truly toddler-friendly!
 * Just import and use. No configuration needed.
 */

import { SimpleClaudeAPI, SimpleConfigImpl } from './simple_api';

// Create a global instance that's ready to use
const globalClaude = new SimpleClaudeAPI(new SimpleConfigImpl({
    model: "sonnet",
    show_thinking: false,
    show_metrics: false,  // Keep it clean for beginners
    verbose: false
}));

/**
 * Ask Claude a question. That's it!
 * @param question - What you want to ask
 * @returns Promise with the answer as a string
 */
export async function claude(question: string): Promise<string> {
    const response = await globalClaude.ask(question);
    return response.text;
}

/**
 * Ask Claude and get the full response with metrics
 * @param question - What you want to ask
 * @returns Promise with full response object
 */
export async function claudeWithInfo(question: string) {
    return await globalClaude.ask(question);
}

/**
 * Ask Claude and show pretty output in terminal
 * @param question - What you want to ask
 */
export async function claudePretty(question: string): Promise<string> {
    // Temporarily enable metrics for this call
    const oldMetrics = globalClaude['config'].show_metrics;
    globalClaude['config'].show_metrics = true;
    
    const response = await globalClaude.ask(question);
    
    // Restore original setting
    globalClaude['config'].show_metrics = oldMetrics;
    
    return response.text;
}

/**
 * Have a conversation with multiple questions
 * @param questions - Array of questions to ask in sequence
 * @returns Array of answers
 */
export async function claudeChat(questions: string[]): Promise<string[]> {
    const answers: string[] = [];
    for (const question of questions) {
        const answer = await claude(question);
        answers.push(answer);
    }
    return answers;
}

/**
 * Ask Claude to think out loud (show reasoning)
 * @param question - What you want to ask
 * @returns The answer as a string
 */
export async function claudeThink(question: string): Promise<string> {
    const oldThinking = globalClaude['config'].show_thinking;
    globalClaude['config'].show_thinking = true;
    
    const response = await globalClaude.ask(question);
    
    globalClaude['config'].show_thinking = oldThinking;
    return response.text;
}

/**
 * Change the AI model (sonnet, opus, haiku)
 * @param model - The model to use
 */
export function useModel(model: 'sonnet' | 'opus' | 'haiku'): void {
    globalClaude.change_model(model);
}

/**
 * Set a system prompt that affects all future questions
 * @param prompt - The system prompt to use
 */
export function setPersonality(prompt: string): void {
    globalClaude.set_system_prompt(prompt);
}

/**
 * Clear the system prompt
 */
export function clearPersonality(): void {
    globalClaude.set_system_prompt();
}

/**
 * Get usage statistics
 */
export function getStats() {
    return globalClaude.get_metrics();
}

/**
 * Reset usage statistics
 */
export function resetStats(): void {
    globalClaude.reset_metrics();
}

// Default export for even simpler usage
export default claude;