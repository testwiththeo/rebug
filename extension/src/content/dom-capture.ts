import type { DomMutationData } from "@/src/lib/types";
import type { CaptureContext, CaptureController } from "./capture";
import { getElementSelector } from "./selectors";
import { maskElementAttributes, maskSensitiveText } from "./sensitive";

const MAX_NODE_HTML_LENGTH = 1_000;
const MAX_NODES_PER_MUTATION = 5;

export function startDomCapture(context: CaptureContext): CaptureController {
  const target = document.documentElement;
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      const data = serializeMutation(mutation);
      context.emit({
        type: "dom_mutation",
        category: mutation.type,
        data,
      });
    }
  });

  observer.observe(target, {
    subtree: true,
    childList: true,
    attributes: true,
    characterData: true,
    attributeOldValue: true,
    characterDataOldValue: true,
  });

  return {
    stop: () => observer.disconnect(),
  };
}

function serializeMutation(mutation: MutationRecord): DomMutationData {
  const data: DomMutationData = {
    type: mutation.type,
    target_selector: getElementSelector(mutation.target),
  };

  if (mutation.type === "attributes") {
    data.attribute_name = mutation.attributeName;
    data.old_value = mutation.oldValue;
    data.new_value =
      mutation.target instanceof Element && mutation.attributeName
        ? mutation.target.getAttribute(mutation.attributeName)
        : null;
  }

  if (mutation.type === "characterData") {
    data.old_value = mutation.oldValue;
    data.new_value = mutation.target.textContent;
  }

  if (mutation.addedNodes.length > 0) {
    data.added_nodes = serializeNodeList(mutation.addedNodes);
  }

  if (mutation.removedNodes.length > 0) {
    data.removed_nodes = serializeNodeList(mutation.removedNodes);
  }

  // Mask sensitive attribute values
  if (data.new_value && typeof data.new_value === "string") {
    data.new_value = maskSensitiveText(data.new_value);
  }
  if (data.old_value && typeof data.old_value === "string") {
    data.old_value = maskSensitiveText(data.old_value);
  }

  return data;
}

function serializeNodeList(nodes: NodeList): string[] {
  return Array.from(nodes)
    .slice(0, MAX_NODES_PER_MUTATION)
    .map(serializeNode)
    .filter(Boolean);
}

function serializeNode(node: Node): string {
  if (node instanceof Element) {
    const html = node.outerHTML.slice(0, MAX_NODE_HTML_LENGTH);
    return maskElementAttributes(html);
  }

  const text = (node.textContent ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, MAX_NODE_HTML_LENGTH);
  return maskSensitiveText(text);
}
