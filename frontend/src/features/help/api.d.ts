export interface HelpArticle {
  id: number;
  question: string;
  answer: string;
  category: string;
  order: number;
}

export function getHelpArticles(category?: string): Promise<HelpArticle[]>;
export function submitHelpRequest(subject: string, message: string): Promise<unknown>;
